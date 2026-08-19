# Basalt RAG

**Basalt RAG** is a citation-first retrieval layer for the Basalt security platform. It indexes the shared control catalogue and normalized current findings, then produces grounded answer material for three questions that security teams must be able to audit:

1. **Why is this a risk?** The answer cites the finding’s severity, risk factors, affected resource, and observed evidence.
2. **Which control is implicated?** The answer cites an actual, namespaced Basalt Core control identifier and its catalogue metadata.
3. **What remediation is available?** The answer cites scanner-provided remediation text, commands, patches, and references without inventing instructions.

The package is deliberately **offline-first**. It performs deterministic lexical retrieval and structured grounding locally. It makes no model-provider, cloud, telemetry, or credential calls. A later agent or chat service may consume its `PromptEnvelope`, but every generated claim must retain this package’s evidence-bound citations.

## Architecture

```text
Basalt Core controls.json ──┐
                           ├─> source documents ─> BM25 retrieval index ─> ranked citations
Basalt Warehouse current   ─┘                                            │
findings mart / native scan                                               ▼
                                                              grounded answer material
                                                          risk · controls · remediation
```

| Component | Responsibility |
|---|---|
| `CatalogDocumentBuilder` | Loads and validates qualified control IDs from Basalt Core. |
| `FindingDocumentBuilder` | Converts current findings or native scan findings into retrievable, provenance-preserving documents. |
| `RetrievalIndex` | Deterministic BM25 retrieval with exact identifier boosts and corpus digesting. |
| `GroundedExplainer` | Produces answer sections only from cited source documents. |
| `CitationValidator` | Rejects unknown controls, missing sources, duplicate citation IDs, and content-digest mismatches. |

## Quick start

```bash
pip install basalt-rag

# Build an offline index from a native Basalt scan artifact.
basalt-rag index scan-result.json --output posture.index.json

# Retrieve cited source material.
basalt-rag search posture.index.json "why is public blob access a risk" --top-k 4

# Explain one normalized finding by fingerprint.
basalt-rag explain posture.index.json --fingerprint 2b5c... --format json
```

`index` always includes the Basalt Core control catalogue. Finding documents are added from either a native `ScanResult` or a JSON export shaped like the Warehouse `fct_current_findings` mart. The generated index stores document text, deterministic term statistics, source locators, and SHA-256 digests; it does **not** store secrets or cloud credentials.

## Citation contract

Every response includes citations with a stable document ID, source kind, exact source locator, content digest, and excerpt. A cited control must resolve through `basalt_core.load_catalog()`. A cited finding must be traceable to a fingerprint and resource URN. A cited remediation must come from the finding’s `remediation` field.

> The shipped Basalt control catalogues are seed subsets and identify themselves as non-authoritative. Basalt RAG preserves the framework source URL and authority flag; it must not be used as an audit-attestation engine without a pinned, official catalogue.

## Development

```bash
make install
make check
make build
python -m twine check dist/*
```

The quality gate runs Ruff linting and formatting, strict mypy, branch coverage at 85% or higher, deterministic retrieval tests, citation integrity tests, and distribution validation.

## Integration boundary

Basalt RAG consumes immutable evidence from Basalt Core or the Warehouse current-findings mart. It does not scan cloud accounts, mutate warehouse history, execute remediation, or independently claim that a control is compliant. Its responsibility is retrieval, grounding, and citation integrity.

## License

Apache License 2.0. See [`LICENSE`](./LICENSE).
