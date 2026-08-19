"""Reusable, deterministic Basalt finding fixtures for retrieval evaluation."""

from __future__ import annotations

from datetime import datetime, timezone

from basalt_core import (
    Evidence,
    Exploitability,
    Exposure,
    Finding,
    Provider,
    Remediation,
    ResourceRef,
    ScanMetadata,
    ScanResult,
    Severity,
)


def public_bucket_finding() -> Finding:
    return Finding(
        rule_id="s3.public-read",
        title="S3 bucket allows public read access",
        description="The bucket ACL grants READ to the AllUsers group.",
        severity=Severity.CRITICAL,
        exposure=Exposure.PUBLIC,
        exploitability=Exploitability.TRIVIAL,
        resource=ResourceRef(
            provider=Provider.AWS,
            resource_type="AWS::S3::Bucket",
            uid="arn:aws:s3:::customer-export-prod",
            account="111122223333",
            region="us-east-1",
        ),
        scanner="basalt-aws",
        scanner_version="0.1.1",
        control_ids=["cis-aws:storage.bucket-public-access", "nist-800-53-r5:AC-3"],
        evidence=[
            Evidence(
                description="Bucket ACL grant",
                observed="AllUsers:READ",
                expected="no public grants",
                source="s3:GetBucketAcl",
            )
        ],
        remediation=Remediation(
            summary="Enable all S3 Block Public Access settings and remove public ACL grants.",
            console_steps=["Enable Block Public Access.", "Remove the AllUsers ACL grant."],
            references=[
                "https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html"
            ],
        ),
        observed_at=datetime(2026, 8, 19, 10, tzinfo=timezone.utc),
    )


def privileged_pod_finding() -> Finding:
    return Finding(
        rule_id="pod.privileged",
        title="Container runs as privileged",
        description="A production workload requests privileged execution.",
        severity=Severity.CRITICAL,
        exposure=Exposure.INTERNAL,
        exploitability=Exploitability.MODERATE,
        resource=ResourceRef(
            provider=Provider.KUBERNETES,
            resource_type="apps/v1/DaemonSet",
            uid="observability/node-agent",
            account="prod-west-01",
            region="us-west-2",
        ),
        scanner="basalt-k8s",
        scanner_version="0.1.0",
        control_ids=["cis-k8s:pod.no-privileged", "nist-800-53-r5:CM-6"],
        evidence=[
            Evidence(
                description="Container security context",
                observed={"privileged": True},
                expected={"privileged": False},
                source="apps/v1/DaemonSet",
            )
        ],
        remediation=Remediation(
            summary="Remove privileged: true and grant only required Linux capabilities."
        ),
        observed_at=datetime(2026, 8, 19, 11, tzinfo=timezone.utc),
    )


def scan_result() -> ScanResult:
    return ScanResult(
        metadata=ScanMetadata(
            scanner="basalt-aws",
            scanner_version="0.1.1",
            provider=Provider.AWS,
            account="111122223333",
            regions=["us-east-1"],
            started_at=datetime(2026, 8, 19, 9, tzinfo=timezone.utc),
            completed_at=datetime(2026, 8, 19, 10, tzinfo=timezone.utc),
            checks_run=12,
        ),
        findings=[public_bucket_finding(), privileged_pod_finding()],
    )
