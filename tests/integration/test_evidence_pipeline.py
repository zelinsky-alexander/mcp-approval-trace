import json
from pathlib import Path

from approvaltrace.evidence.bundle import finalize_bundle
from approvaltrace.evidence.manifest import verify_manifest


def test_builds_verifiable_static_evidence_bundle(tmp_path: Path) -> None:
    scenario = tmp_path / "AT-001.yaml"
    scenario.write_text("id: AT-001\ntitle: clean\n", encoding="utf-8")
    server_tool = {
        "name": "search_test_documents",
        "description": "Search test documents.",
        "inputSchema": {"type": "object"},
    }
    body = {
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "search_test_documents",
                    "description": "Search test documents.",
                    "inputSchema": {"type": "object"},
                },
            }
        ]
    }
    run_dir = tmp_path / "run"

    report = finalize_bundle(
        run_dir=run_dir,
        scenario_file=scenario,
        server_tool=server_tool,
        model_body=body,
        findings={"result": "PASS"},
    )

    assert report.exists()
    assert json.loads((run_dir / "findings.json").read_text())["result"] == "PASS"
    assert verify_manifest(run_dir) == []
