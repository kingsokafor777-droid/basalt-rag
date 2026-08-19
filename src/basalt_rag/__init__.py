"""Citation-first, deterministic retrieval for Basalt security findings and controls."""

from .grounding import GroundedExplainer
from .index import RetrievalIndex
from .ingest import CatalogIntegrityError, catalog_documents, finding_documents
from .models import Citation, GroundedAnswer, PromptEnvelope, SourceDocument, SourceKind

__all__ = [
    "CatalogIntegrityError",
    "Citation",
    "GroundedAnswer",
    "GroundedExplainer",
    "PromptEnvelope",
    "RetrievalIndex",
    "SourceDocument",
    "SourceKind",
    "catalog_documents",
    "finding_documents",
]

__version__ = "0.1.0"
