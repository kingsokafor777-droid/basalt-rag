# ADR 0001: Citation-first deterministic retrieval

## Context

Security explanations are harmful when their evidence cannot be traced to a finding observation, a catalogued control, or a scanner-provided remediation record. A free-form answer layer may be useful later, but cannot be the source of truth.

## Decision

Basalt RAG builds a local, deterministic BM25 index and produces structured answer material with mandatory citations. Citation validation occurs when documents are added, when the index is persisted or loaded, and when answer material is assembled. The package does not call an LLM.

## Consequences

The system is reproducible, credential-free, cheap to operate, and suitable as a grounding layer for a later LLM agent. Semantic retrieval and generated prose are delegated to optional consumers, which must preserve and validate the supplied citation set.
