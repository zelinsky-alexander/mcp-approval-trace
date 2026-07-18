import json
from pathlib import Path

from fastapi.testclient import TestClient

from approvaltrace.capture_api.app import create_app


def test_captures_chat_completions_request(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path))
    client.post(
        "/approvaltrace/activate",
        json={"run_id": "run-001", "scenario_id": "AT-001", "phase": "initial"},
    )
    payload = {
        "model": "approvaltrace-capture",
        "messages": [{"role": "user", "content": "test"}],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "search_test_documents",
                    "description": "Search test documents.",
                    "parameters": {"type": "object"},
                },
            }
        ],
    }

    response = client.post(
        "/v1/chat/completions",
        json=payload,
        headers={"Authorization": "Bearer secret-value"},
    )

    assert response.status_code == 200
    captures = client.get("/approvaltrace/runs/run-001/captures").json()
    assert len(captures) == 1
    assert captures[0]["extracted_tools"][0]["function"]["name"] == "search_test_documents"
    raw_path = tmp_path / "runs" / "run-001" / "captures" / "model-request-001.raw.json"
    assert json.loads(raw_path.read_text(encoding="utf-8")) == payload


def test_supports_responses_api(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path))
    response = client.post(
        "/v1/responses",
        json={"model": "approvaltrace-capture", "input": "test", "tools": []},
    )

    assert response.status_code == 200
    assert response.json()["object"] == "response"
