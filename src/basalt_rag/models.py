"""Typed, serializable contracts for retrievable Basalt evidence and citations."""

from __future__ import annotations

import hashlib
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SourceKind(str, Enum):
    """Source families allowed to support a grounded response."""

    CONTROL = "control"
    FINDING = "finding"


class SourceLocator(BaseModel):
    """Stable source address and provenance preserved with every document."""

    model_config = ConfigDict(frozen=True)

    uri: str = Field(min_length=1)
    description: str = Field(min_length=1)


class SourceDocument(BaseModel):
    """A retrievable source record; content is always preserved, never synthesized later."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    kind: SourceKind
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    locator: SourceLocator
    metadata: dict[str, str] = Field(default_factory=dict)

    @field_validator("id")
    @classmethod
    def _stable_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized or any(character.isspace() for character in normalized):
            raise ValueError("document id must be a non-empty, whitespace-free stable identifier")
        return normalized

    @property
    def digest(self) -> str:
        """Digest binds citation content to the exact indexed source record."""
        source = "\n".join([self.id, self.kind.value, self.title, self.content, self.locator.uri])
        return hashlib.sha256(source.encode("utf-8")).hexdigest()


class Citation(BaseModel):
    """A verifiable claim source included in a response or retrieval result."""

    model_config = ConfigDict(frozen=True)

    document_id: str = Field(min_length=1)
    source_kind: SourceKind
    source_uri: str = Field(min_length=1)
    digest: str = Field(min_length=64, max_length=64)
    excerpt: str = Field(min_length=1)
    control_id: str | None = None
    finding_fingerprint: str | None = None


class SearchHit(BaseModel):
    """A ranked source document and its evidence-bound citation."""

    model_config = ConfigDict(frozen=True)

    document: SourceDocument
    score: float = Field(ge=0)
    citation: Citation


class GroundedAnswer(BaseModel):
    """Structured answer material whose claims map to the included citation set."""

    model_config = ConfigDict(frozen=True)

    finding_fingerprint: str
    risk_rationale: str
    implicated_controls: list[str]
    remediation_guidance: str
    citations: list[Citation] = Field(min_length=1)


class PromptEnvelope(BaseModel):
    """Evidence packet for an optional downstream LLM; it is not an LLM response."""

    model_config = ConfigDict(frozen=True)

    query: str = Field(min_length=1)
    instructions: str = Field(min_length=1)
    sources: list[SearchHit] = Field(min_length=1)
