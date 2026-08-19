from __future__ import annotations

import json

from basalt_rag.cli import main

from .helpers import scan_result


def test_index_search_and_explain_cli_flow(tmp_path, capsys) -> None:
    source = tmp_path / "scan.json"
    output = tmp_path / "posture.index.json"
    result = scan_result()
    source.write_text(result.model_dump_json(), encoding="utf-8")

    assert main(["index", "--native-scan", str(source), "--output", str(output)]) == 0
    index_stdout = json.loads(capsys.readouterr().out)
    assert index_stdout["documents"] > 2

    assert main(["search", str(output), "public bucket access", "--top-k", "3"]) == 0
    search_stdout = json.loads(capsys.readouterr().out)
    assert search_stdout["sources"]

    fingerprint = result.findings[0].fingerprint
    assert main(["explain", str(output), "--fingerprint", fingerprint]) == 0
    explanation = json.loads(capsys.readouterr().out)
    assert explanation["finding_fingerprint"] == fingerprint
    assert explanation["citations"]
