"""Command line interface for building and querying citation-first Basalt RAG indexes."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from .grounding import GroundedExplainer
from .index import RetrievalIndex
from .ingest import catalog_documents, current_finding_documents, documents_from_native_path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="basalt-rag", description="Citation-first Basalt retrieval"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    index = commands.add_parser("index", help="Build a local deterministic retrieval index")
    source = index.add_mutually_exclusive_group(required=True)
    source.add_argument("--native-scan", type=Path, help="Lossless native Basalt ScanResult JSON")
    source.add_argument(
        "--warehouse-current", type=Path, help="JSON list exported from fct_current_findings"
    )
    index.add_argument("--output", required=True, type=Path, help="Output index JSON path")
    search = commands.add_parser("search", help="Retrieve cited evidence")
    search.add_argument("index", type=Path)
    search.add_argument("query")
    search.add_argument("--top-k", type=int, default=5)
    explain = commands.add_parser("explain", help="Explain a finding by stable fingerprint")
    explain.add_argument("index", type=Path)
    explain.add_argument("--fingerprint", required=True)
    return parser


def _load_warehouse_rows(path: Path) -> list[dict[str, object]]:
    raw: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list) or not all(isinstance(row, dict) for row in raw):
        raise ValueError("warehouse-current input must be a JSON list of current finding objects")
    return [dict(row) for row in raw]


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return a conventional process exit code."""
    args = _parser().parse_args(argv)
    if args.command == "index":
        documents = (
            documents_from_native_path(args.native_scan)
            if args.native_scan
            else [
                *catalog_documents(),
                *current_finding_documents(_load_warehouse_rows(args.warehouse_current)),
            ]
        )
        index = RetrievalIndex(documents=documents)
        index.save(args.output)
        print(
            json.dumps(
                {"documents": len(index.documents), "corpus_digest": index.corpus_digest}, indent=2
            )
        )
        return 0
    index = RetrievalIndex.load(args.index)
    explainer = GroundedExplainer(index)
    if args.command == "search":
        print(explainer.retrieve(args.query, top_k=args.top_k).model_dump_json(indent=2))
        return 0
    if args.command == "explain":
        print(explainer.explain_finding(args.fingerprint).model_dump_json(indent=2))
        return 0
    raise AssertionError(f"unsupported command: {args.command}")
