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


def test_streams_chat_completions_when_requested(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path))
    client.post(
        "/approvaltrace/activate",
        json={"run_id": "run-stream", "scenario_id": "AT-001", "phase": "initial"},
    )

    with client.stream(
        "POST",
        "/v1/chat/completions",
        json={
            "model": "approvaltrace-capture",
            "messages": [{"role": "user", "content": "test"}],
            "stream": True,
            "stream_options": {"include_usage": True},
        },
    ) as response:
        body = "".join(response.iter_text())

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert '"object":"chat.completion.chunk"' in body
    assert '"content":"ApprovalTrace capture complete."' in body
    assert '"usage":{"prompt_tokens":0,"completion_tokens":0,"total_tokens":0}' in body
    assert body.endswith("data: [DONE]\n\n")
    captures = client.get("/approvaltrace/runs/run-stream/captures").json()
    assert len(captures) == 1


def test_uses_cline_plan_completion_wrapper(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path))
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "approvaltrace-capture",
            "messages": [
                {
                    "role": "system",
                    "content": "Use <plan_mode_respond> to return the final response.",
                },
                {"role": "user", "content": "test"},
            ],
        },
    )

    content = response.json()["choices"][0]["message"]["content"]
    assert content == (
        "<plan_mode_respond>\n"
        "<response>ApprovalTrace capture complete.</response>\n"
        "</plan_mode_respond>"
    )
