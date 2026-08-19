# Security Policy

## Reporting a vulnerability

Please report suspected vulnerabilities privately through GitHub Security Advisories for this repository. Do not publish proofs of concept that expose credentials, customer data, or security-sensitive deployment details.

## Data handling

Basalt RAG is offline-first and does not send documents to a model provider. Inputs may nevertheless contain sensitive resource identifiers, evidence, remediation notes, or source locations. Store persisted indexes only in approved locations, encrypt them at rest where required, and treat exported answer material as security-sensitive.

## Trust boundary

The package validates control references against the configured Basalt catalogue and binds citations to indexed evidence. It does not independently verify cloud state, validate that a remediation has been applied, or convert seed controls into an audit attestation.
