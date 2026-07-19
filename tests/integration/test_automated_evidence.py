from pathlib import Path

from approvaltrace.automation.evidence import build_run_evidence
from approvaltrace.evidence.manifest import verify_manifest


def test_builds_automated_evidence_for_cline_prompt(tmp_path: Path) -> None:
    scenario_file = tmp_path / "scenario.yaml"
    scenario_file.write_text("id: AT-001\ntitle: Clean\n", encoding="utf-8")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "approval-before.png").write_bytes(b"png")
    tool = {
        "name": "search_test_documents",
        "description": "Search test documents.",
        "inputSchema": {"type": "object", "properties": {}},
    }
    capture = {
        "request_number": 1,
        "phase": "initial",
        "body": {
            "messages": [
                {
                    "role": "system",
                    "content": """## approvaltrace (`python -m mutation_server.server`)
### Available Tools
- search_test_documents: Search test documents.
    Input Schema:
    {"type":"object","properties":{}}
====
""",
                }
            ]
        },
    }

    method, complete = build_run_evidence(
        run_dir=run_dir,
        scenario_file=scenario_file,
        initial_tool=tool,
        mutated_tool=None,
        captures=[capture],
        ui_observation={
            "approval_shown": False,
            "visible_fields": {"tool_name": "full", "tool_description": "full"},
        },
        environment={
            "run_id": "cline-at001-001",
            "client_name": "Cline",
            "client_version": "4.0.9",
            "operating_system": "Windows",
        },
        timeline=[],
        findings={"result": "PASS", "severity": "info", "reasons": []},
    )

    assert method == "cline_system_prompt"
    assert complete is True
    assert verify_manifest(run_dir) == []
