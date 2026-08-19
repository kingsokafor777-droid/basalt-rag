"""Converts Basalt Core and Warehouse records into citation-safe source documents."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

from basalt_core import Finding, ScanResult, load_catalog
from basalt_core.controls import ControlCatalog, qualify

from .models import SourceDocument, SourceKind, SourceLocator


class CatalogIntegrityError(ValueError):
    """Raised when a finding references an unknown or malformed Basalt control ID."""


def catalog_documents(catalog: ControlCatalog | None = None) -> list[SourceDocument]:
    """Build one source document per real qualified control in the configured catalogue."""
    resolved_catalog = catalog or load_catalog()
    documents: list[SourceDocument] = []
    for framework in resolved_catalog.frameworks:
        source_url = framework.source or f"catalog://{framework.id}"
        for control in framework.controls:
            qualified_id = qualify(framework.id, control.id)
            content = "\n".join(
                [
                    f"Control ID: {qualified_id}",
                    f"Framework: {framework.name} ({framework.version})",
                    f"Title: {control.title}",
                    f"Family: {control.family or 'not specified'}",
                    "Description: "
                    f"{control.description or 'No additional description in catalogue.'}",
                    "Catalogue authority: "
                    f"{'authoritative' if framework.authoritative else 'seed subset'}",
                ]
            )
            documents.append(
                SourceDocument(
                    id=f"control:{qualified_id}",
                    kind=SourceKind.CONTROL,
                    title=control.title,
                    content=content,
                    locator=SourceLocator(
                        uri=source_url,
                        description=f"{framework.name} control {qualified_id}",
                    ),
                    metadata={
                        "control_id": qualified_id,
                        "framework": framework.id,
                        "framework_version": framework.version,
                        "authoritative": str(framework.authoritative).lower(),
                    },
                )
            )
    return documents


def _validate_control_ids(control_ids: Iterable[str], catalog: ControlCatalog) -> list[str]:
    normalized = sorted({control_id.strip() for control_id in control_ids if control_id.strip()})
    unknown = catalog.unknown(normalized)
    if unknown:
        raise CatalogIntegrityError(
            f"finding references unknown Basalt control IDs: {', '.join(unknown)}"
        )
    return normalized


def _finding_content(finding: Finding, control_ids: list[str]) -> str:
    evidence = (
        "; ".join(
            f"{item.description}; observed={item.observed!r}; expected={item.expected!r}; "
            f"source={item.source or 'unspecified'}"
            for item in finding.evidence
        )
        or "No structured evidence was supplied by the scanner."
    )
    remediation = (
        finding.remediation.summary if finding.remediation else "No remediation was supplied."
    )
    remediation_references = (
        ", ".join(finding.remediation.references) if finding.remediation else ""
    )
    return "\n".join(
        [
            f"Finding fingerprint: {finding.fingerprint}",
            f"Rule: {finding.rule_id}",
            f"Title: {finding.title}",
            f"Description: {finding.description}",
            f"Severity: {finding.severity.value}",
            f"Risk: {finding.risk.value} ({finding.risk.band}); {finding.risk.explain()}",
            f"Exposure: {finding.exposure.value}; exploitability: {finding.exploitability.value}",
            f"Scanner: {finding.scanner}@{finding.scanner_version}",
            f"Resource: {finding.resource.urn}",
            f"Mapped controls: {', '.join(control_ids) or 'none'}",
            f"Evidence: {evidence}",
            f"Remediation: {remediation}",
            f"Remediation references: {remediation_references or 'none'}",
        ]
    )


def finding_documents(
    findings: Iterable[Finding], catalog: ControlCatalog | None = None
) -> list[SourceDocument]:
    """Index native findings while retaining their exact evidence and remediation provenance."""
    resolved_catalog = catalog or load_catalog()
    documents: list[SourceDocument] = []
    for finding in findings:
        control_ids = _validate_control_ids(finding.control_ids, resolved_catalog)
        remediation = finding.remediation.summary if finding.remediation else ""
        evidence = " | ".join(item.description for item in finding.evidence)
        evidence_detail = " | ".join(
            f"{item.description}; observed={item.observed!r}; expected={item.expected!r}"
            for item in finding.evidence
        )
        documents.append(
            SourceDocument(
                id=f"finding:{finding.fingerprint}",
                kind=SourceKind.FINDING,
                title=finding.title,
                content=_finding_content(finding, control_ids),
                locator=SourceLocator(
                    uri=f"basalt://finding/{finding.fingerprint}",
                    description=f"{finding.scanner} observation for {finding.resource.urn}",
                ),
                metadata={
                    "finding_fingerprint": finding.fingerprint,
                    "rule_id": finding.rule_id,
                    "severity": finding.severity.value,
                    "risk_score": str(finding.risk.value),
                    "risk_band": str(finding.risk.band),
                    "resource_urn": finding.resource.urn,
                    "scanner": finding.scanner,
                    "control_ids": "|".join(control_ids),
                    "evidence_summary": evidence,
                    "evidence_detail": evidence_detail,
                    "remediation_summary": remediation,
                },
            )
        )
    return documents


def read_native_scan(path: Path) -> ScanResult:
    """Read a lossless native Basalt JSON artifact through the canonical Core validator."""
    return ScanResult.model_validate_json(path.read_text(encoding="utf-8"))


def _as_control_ids(value: object) -> list[str]:
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    if isinstance(value, str):
        try:
            parsed: object = json.loads(value)
        except json.JSONDecodeError:
            return [part.strip() for part in value.split(",") if part.strip()]
        if isinstance(parsed, list) and all(isinstance(item, str) for item in parsed):
            return parsed
    raise ValueError(
        "warehouse current finding control_ids must be a string list or JSON string list"
    )


def current_finding_documents(
    rows: Sequence[Mapping[str, object]], catalog: ControlCatalog | None = None
) -> list[SourceDocument]:
    """Convert Warehouse ``fct_current_findings`` rows into current-posture documents.

    Warehouse rows already represent the latest complete scan inside a comparable scope. This
    function preserves that boundary rather than inventing a mutable finding status.
    """
    resolved_catalog = catalog or load_catalog()
    documents: list[SourceDocument] = []
    required = {
        "fingerprint",
        "rule_id",
        "title",
        "severity",
        "risk_score",
        "resource_urn",
        "control_ids",
    }
    for row in rows:
        missing = sorted(key for key in required if not row.get(key))
        if missing:
            raise ValueError(
                f"warehouse current finding is missing required fields: {', '.join(missing)}"
            )
        fingerprint = str(row["fingerprint"])
        control_ids = _validate_control_ids(_as_control_ids(row["control_ids"]), resolved_catalog)
        remediation = str(row.get("remediation_summary") or "No remediation was supplied.")
        evidence = str(
            row.get("evidence") or "Warehouse current finding evidence is retained in raw payload."
        )
        content = "\n".join(
            [
                f"Finding fingerprint: {fingerprint}",
                f"Rule: {row['rule_id']}",
                f"Title: {row['title']}",
                f"Severity: {row['severity']}",
                f"Risk score: {row['risk_score']}",
                f"Resource: {row['resource_urn']}",
                f"Mapped controls: {', '.join(control_ids) or 'none'}",
                f"Evidence: {evidence}",
                f"Remediation: {remediation}",
            ]
        )
        documents.append(
            SourceDocument(
                id=f"finding:{fingerprint}",
                kind=SourceKind.FINDING,
                title=str(row["title"]),
                content=content,
                locator=SourceLocator(
                    uri=f"warehouse://analytics.fct_current_findings/{fingerprint}",
                    description=(
                        f"Current finding for scope {row.get('scope_key') or 'unspecified'}"
                    ),
                ),
                metadata={
                    "finding_fingerprint": fingerprint,
                    "rule_id": str(row["rule_id"]),
                    "severity": str(row["severity"]),
                    "risk_score": str(row["risk_score"]),
                    "resource_urn": str(row["resource_urn"]),
                    "scanner": str(row.get("scanner") or "warehouse"),
                    "control_ids": "|".join(control_ids),
                    "evidence_summary": evidence,
                    "evidence_detail": evidence,
                    "remediation_summary": remediation,
                },
            )
        )
    return documents


def documents_from_native_path(
    path: Path, catalog: ControlCatalog | None = None
) -> list[SourceDocument]:
    """Build a complete corpus from the shared catalogue and a validated native scan result."""
    resolved_catalog = catalog or load_catalog()
    findings = finding_documents(read_native_scan(path).findings, resolved_catalog)
    return [*catalog_documents(resolved_catalog), *findings]
