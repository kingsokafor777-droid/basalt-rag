"""Deterministic BM25 retrieval index with corpus and citation integrity validation."""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter, defaultdict
from collections.abc import Iterable
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .models import Citation, SearchHit, SourceDocument, SourceKind

_TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9._:-]*")
_INDEX_VERSION = "1"


class IndexIntegrityError(ValueError):
    """Raised when serialized retrieval state cannot support verified citations."""


def tokenize(text: str) -> list[str]:
    """Normalize lexical terms while retaining qualified controls and identifiers."""
    return _TOKEN_PATTERN.findall(text.lower())


def citation_for(document: SourceDocument, *, excerpt_length: int = 320) -> Citation:
    """Create a source-bound citation that records the indexed-content digest."""
    return Citation(
        document_id=document.id,
        source_kind=document.kind,
        source_uri=document.locator.uri,
        digest=document.digest,
        excerpt=document.content[:excerpt_length].strip(),
        control_id=document.metadata.get("control_id"),
        finding_fingerprint=document.metadata.get("finding_fingerprint"),
    )


class RetrievalIndex(BaseModel):
    """Serializable corpus plus a deterministic, in-memory BM25 scoring implementation."""

    model_config = ConfigDict(frozen=True)

    version: str = _INDEX_VERSION
    documents: list[SourceDocument] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_documents(self) -> RetrievalIndex:
        ids = [document.id for document in self.documents]
        if len(ids) != len(set(ids)):
            raise IndexIntegrityError("document IDs must be unique")
        for document in self.documents:
            if document.kind is SourceKind.CONTROL and not document.metadata.get("control_id"):
                raise IndexIntegrityError(
                    f"control document {document.id} is missing control_id metadata"
                )
            if document.kind is SourceKind.FINDING and not document.metadata.get(
                "finding_fingerprint"
            ):
                raise IndexIntegrityError(
                    f"finding document {document.id} is missing finding_fingerprint metadata"
                )
        return self

    @property
    def corpus_digest(self) -> str:
        """Stable digest that allows callers to identify the exact indexed source set."""
        content = "\n".join(
            f"{document.id}:{document.digest}"
            for document in sorted(self.documents, key=lambda item: item.id)
        )
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def document(self, document_id: str) -> SourceDocument:
        """Return a document by stable ID or fail closed if a citation target is absent."""
        for document in self.documents:
            if document.id == document_id:
                return document
        raise IndexIntegrityError(f"citation references document absent from index: {document_id}")

    def _scores(self, query: str) -> dict[str, float]:
        terms = tokenize(query)
        if not terms:
            raise ValueError("query must contain at least one retrievable token")
        documents_by_id = {document.id: document for document in self.documents}
        token_counts = {
            document_id: Counter(tokenize(f"{document.title}\n{document.content}"))
            for document_id, document in documents_by_id.items()
        }
        document_lengths = {
            document_id: sum(counts.values()) for document_id, counts in token_counts.items()
        }
        average_length = sum(document_lengths.values()) / len(document_lengths)
        document_frequency: defaultdict[str, int] = defaultdict(int)
        for counts in token_counts.values():
            for term in counts:
                document_frequency[term] += 1

        scores: dict[str, float] = {}
        query_lower = query.lower().strip()
        for document_id, document in documents_by_id.items():
            score = 0.0
            for term in terms:
                frequency = token_counts[document_id].get(term, 0)
                if frequency == 0:
                    continue
                inverse_frequency = math.log(
                    1
                    + (len(documents_by_id) - document_frequency[term] + 0.5)
                    / (document_frequency[term] + 0.5)
                )
                k1 = 1.5
                b = 0.75
                denominator = frequency + k1 * (
                    1 - b + b * document_lengths[document_id] / average_length
                )
                score += inverse_frequency * frequency * (k1 + 1) / denominator
            identifiers = {
                document.id.lower(),
                document.metadata.get("control_id", "").lower(),
                document.metadata.get("finding_fingerprint", "").lower(),
                document.metadata.get("rule_id", "").lower(),
            }
            if query_lower in identifiers:
                score += 8.0
            if score > 0:
                scores[document_id] = score
        return scores

    def search(self, query: str, *, top_k: int = 5) -> list[SearchHit]:
        """Return relevance-ranked source records with deterministic tie breaking."""
        if top_k < 1:
            raise ValueError("top_k must be at least one")
        scores = self._scores(query)
        ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:top_k]
        return [
            SearchHit(
                document=self.document(document_id),
                score=score,
                citation=citation_for(self.document(document_id)),
            )
            for document_id, score in ranked
        ]

    def verify_citations(self, citations: Iterable[Citation]) -> None:
        """Fail closed if an answer cites a stale, missing, or modified source document."""
        seen: set[str] = set()
        for citation in citations:
            if citation.document_id in seen:
                raise IndexIntegrityError(f"answer repeats citation {citation.document_id}")
            seen.add(citation.document_id)
            document = self.document(citation.document_id)
            expected = citation_for(document)
            if citation != expected:
                raise IndexIntegrityError(
                    f"citation does not match indexed source: {citation.document_id}"
                )

    def save(self, path: Path) -> None:
        """Persist sources only; deterministic term statistics are rebuilt at read time."""
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> RetrievalIndex:
        """Load and validate a persisted index artifact."""
        return cls.model_validate_json(path.read_text(encoding="utf-8"))
