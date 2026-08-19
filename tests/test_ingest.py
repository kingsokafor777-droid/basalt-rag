from __future__ import annotations

import pytest
from basalt_core import load_catalog

from basalt_rag.ingest import (
    CatalogIntegrityError,
    catalog_documents,
    current_finding_documents,
    finding_documents,
)

from .helpers import public_bucket_finding


def test_catalog_documents_use_real_qualified_control_ids() -> None:
    documents = catalog_documents()

    control = next(
        document
        for document in documents
        if document.id == "control:cis-aws:storage.bucket-public-access"
    )

    assert control.metadata["control_id"] == "cis-aws:storage.bucket-public-access"
    assert control.locator.uri.startswith("https://")
    assert "S3 Block Public Access" in control.content


def test_every_indexed_control_document_resolves_in_basalt_core() -> None:
    catalog = load_catalog()
    documents = catalog_documents(catalog)

    unresolved = [
        document.metadata["control_id"]
        for document in documents
        if catalog.get(document.metadata["control_id"]) is None
    ]

    assert unresolved == []


def test_finding_document_preserves_evidence_remediation_and_controls() -> None:
    finding = public_bucket_finding()

    document = finding_documents([finding])[0]

    assert document.metadata["finding_fingerprint"] == finding.fingerprint
    assert "AllUsers:READ" in document.content
    assert "Enable all S3 Block Public Access" in document.content
    assert "cis-aws:storage.bucket-public-access" in document.metadata["control_ids"]


def test_unknown_controls_fail_before_document_is_created() -> None:
    invalid = public_bucket_finding().model_copy(
        update={"control_ids": ["cis-aws:not-a-real-control"]}
    )

    with pytest.raises(CatalogIntegrityError, match="not-a-real-control"):
        finding_documents([invalid])


def test_current_warehouse_rows_retain_current_finding_provenance() -> None:
    row = {
        "fingerprint": "warehouse-fingerprint",
        "rule_id": "storage.public-blob",
        "title": "Public blob access is enabled",
        "severity": "critical",
        "risk_score": 96,
        "resource_urn": "urn:basalt:azure:subscription:eastus:storage:customerexport",
        "scope_key": "azure-prod",
        "control_ids": '["cis-azure:storage.public-blob-access"]',
        "remediation_summary": "Disable public blob access.",
    }

    document = current_finding_documents([row])[0]

    assert document.locator.uri.endswith("warehouse-fingerprint")
    assert document.metadata["control_ids"] == "cis-azure:storage.public-blob-access"
    assert "Disable public blob access." in document.content
