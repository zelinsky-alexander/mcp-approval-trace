import json
from pathlib import Path

from approvaltrace.automation.dashboard import generate_batch_dashboard


def test_generates_batch_dashboard_with_timeline(tmp_path: Path) -> None:
    run_dir = tmp_path / "runs" / "cline-at001-001"
    run_dir.mkdir(parents=True)
    (run_dir / "event-timeline.json").write_text(
        json.dumps([{"timestamp": "2026-01-01T00:00:00Z", "event": "capture", "phase": "initial"}]),
        encoding="utf-8",
    )
    summary = {
        "generated_at": "2026-01-01T00:00:01Z",
        "client": "Cline 4.0.9",
        "results": [
            {
                "scenario_id": "AT-001",
                "run_id": "cline-at001-001",
                "result": "PASS",
                "model_extraction": "cline_system_prompt",
                "notification_observed": None,
                "automatic_refresh": None,
                "reapproval_observed": False,
                "changed_requests_before_reapproval": 0,
                "evidence_complete": True,
            }
        ],
    }

    path = generate_batch_dashboard(tmp_path, summary)
    text = path.read_text(encoding="utf-8")

    assert "AT-001" in text
    assert "cline-at001-001/report.html" in text
    assert "capture" in text
