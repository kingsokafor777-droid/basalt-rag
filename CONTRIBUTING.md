# Contributing

Changes must preserve three invariants: retrieval is deterministic, every response claim is evidence-bound, and every control citation resolves through a versioned Basalt catalogue.

Run `make check` before opening a pull request. New retrieval behavior requires a focused regression test demonstrating relevance and citation integrity. Changes to the document or citation contract require an ADR because downstream agents may rely on its serialized shape.
