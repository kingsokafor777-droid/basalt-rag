"""Evidence-bound answer assembly for Basalt findings without hidden model calls."""

from __future__ import annotations

from .index import IndexIntegrityError, RetrievalIndex
from .models import Citation, GroundedAnswer, PromptEnvelope, SourceDocument


class GroundedExplainer:
    """Builds auditable response sections only from indexed Basalt source records."""

    def __init__(self, index: RetrievalIndex) -> None:
        self._index = index

    def _finding(self, fingerprint: str) -> SourceDocument:
        document = self._index.document(f"finding:{fingerprint}")
        if document.metadata.get("finding_fingerprint") != fingerprint:
            raise IndexIntegrityError(f"finding document fingerprint mismatch for {fingerprint}")
        return document

    def explain_finding(self, fingerprint: str) -> GroundedAnswer:
        """Explain one finding with its direct evidence, valid controls, and scanner remediation."""
        finding = self._finding(fingerprint)
        control_ids = [item for item in finding.metadata.get("control_ids", "").split("|") if item]
        control_documents = [
            self._index.document(f"control:{control_id}") for control_id in control_ids
        ]
        risk_score = finding.metadata.get("risk_score", "unknown")
        severity = finding.metadata.get("severity", "unknown")
        resource = finding.metadata.get("resource_urn", "unknown resource")
        evidence = (
            finding.metadata.get("evidence_detail")
            or finding.metadata.get("evidence_summary")
            or "No structured evidence was supplied."
        )
        remediation = finding.metadata.get("remediation_summary") or "No remediation was supplied."
        controls = [
            f"{document.metadata['control_id']} — {document.title}"
            for document in control_documents
        ]
        answer = GroundedAnswer(
            finding_fingerprint=fingerprint,
            risk_rationale=(
                f"{finding.title} is recorded as {severity} with a Basalt risk score of "
                f"{risk_score} "
                f"on {resource}. Scanner evidence: {evidence}"
            ),
            implicated_controls=controls,
            remediation_guidance=remediation,
            citations=[self._citation(document) for document in [finding, *control_documents]],
        )
        self._index.verify_citations(answer.citations)
        return answer

    def retrieve(self, query: str, *, top_k: int = 5) -> PromptEnvelope:
        """Create a model-ready but model-independent evidence packet for a user query."""
        hits = self._index.search(query, top_k=top_k)
        if not hits:
            raise LookupError("no indexed Basalt sources matched the query")
        return PromptEnvelope(
            query=query,
            instructions=(
                "Answer only from the supplied sources. Attribute every risk, control, and "
                "remediation "
                "claim to its citation document ID. State when remediation evidence is absent."
            ),
            sources=hits,
        )

    def _citation(self, document: SourceDocument) -> Citation:
        from .index import citation_for

        return citation_for(document)
