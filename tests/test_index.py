from __future__ import annotations

import pytest

from basalt_rag.grounding import GroundedExplainer
from basalt_rag.index import IndexIntegrityError, RetrievalIndex, citation_for
from basalt_rag.ingest import catalog_documents, finding_documents
from basalt_rag.models import Citation

from .helpers import privileged_pod_finding, public_bucket_finding


def build_index() -> RetrievalIndex:
    return RetrievalIndex(
        documents=[
            *catalog_documents(),
            *finding_documents([public_bucket_finding(), privileged_pod_finding()]),
        ]
    )


def test_exact_control_query_boosts_the_control_source() -> None:
    index = build_index()

    hits = index.search("cis-aws:storage.bucket-public-access", top_k=3)

    assert hits[0].document.id == "control:cis-aws:storage.bucket-public-access"
    assert hits[0].citation.control_id == "cis-aws:storage.bucket-public-access"


def test_semantic_terms_retrieve_the_matching_finding_and_control() -> None:
    index = build_index()

    hit_ids = [
        hit.document.id for hit in index.search("public bucket ACL AllUsers remediation", top_k=5)
    ]

    assert f"finding:{public_bucket_finding().fingerprint}" in hit_ids
    assert "control:cis-aws:storage.bucket-public-access" in hit_ids


def test_grounded_explanation_has_finding_and_control_citations() -> None:
    finding = public_bucket_finding()
    answer = GroundedExplainer(build_index()).explain_finding(finding.fingerprint)

    assert answer.finding_fingerprint == finding.fingerprint
    assert "critical" in answer.risk_rationale
    assert "AllUsers:READ" in answer.risk_rationale
    assert answer.implicated_controls[0].startswith("cis-aws:storage.bucket-public-access")
    assert "Enable all S3 Block Public Access" in answer.remediation_guidance
    assert {citation.source_kind.value for citation in answer.citations} == {"finding", "control"}


def test_citation_verification_rejects_digest_tampering() -> None:
    index = build_index()
    document = index.document("control:cis-aws:storage.bucket-public-access")
    valid = citation_for(document)
    tampered = Citation.model_construct(**{**valid.model_dump(), "digest": "0" * 64})

    with pytest.raises(IndexIntegrityError, match="does not match"):
        index.verify_citations([tampered])


def test_persisted_index_round_trip_preserves_digest_and_results(tmp_path) -> None:
    index = build_index()
    path = tmp_path / "posture.index.json"
    index.save(path)

    loaded = RetrievalIndex.load(path)

    assert loaded.corpus_digest == index.corpus_digest
    assert [hit.document.id for hit in loaded.search("privileged pod", top_k=2)] == [
        hit.document.id for hit in index.search("privileged pod", top_k=2)
    ]
