from __future__ import annotations

import hashlib
import os
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request

from approvaltrace.capture_api.models import ActivateScenarioRequest, CaptureRecord
from approvaltrace.capture_api.redaction import redact
from approvaltrace.capture_api.storage import CaptureStore


def _extract_tools(body: dict[str, Any]) -> list[dict[str, Any]]:
    tools = body.get("tools")
    if isinstance(tools, list):
        return [item for item in tools if isinstance(item, dict)]
    return []


def _canned_chat_response() -> dict[str, Any]:
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "approvaltrace-capture",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "ApprovalTrace capture complete.",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


def _canned_responses_api() -> dict[str, Any]:
    return {
        "id": f"resp_{uuid.uuid4().hex[:12]}",
        "object": "response",
        "created_at": int(time.time()),
        "status": "completed",
        "model": "approvaltrace-capture",
        "output": [
            {
                "id": f"msg_{uuid.uuid4().hex[:12]}",
                "type": "message",
                "role": "assistant",
                "content": [
                    {
                        "type": "output_text",
                        "text": "ApprovalTrace capture complete.",
                        "annotations": [],
                    }
                ],
            }
        ],
    }


def create_app(root: Path | None = None) -> FastAPI:
    evidence_root = root or Path(os.environ.get("APPROVALTRACE_ROOT", ".approvaltrace"))
    store = CaptureStore(evidence_root)
    app = FastAPI(title="MCP ApprovalTrace Capture API", version="0.1.0")
    app.state.store = store

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/v1/models")
    def models() -> dict[str, Any]:
        return {
            "object": "list",
            "data": [
                {
                    "id": "approvaltrace-capture",
                    "object": "model",
                    "created": 0,
                    "owned_by": "approvaltrace",
                }
            ],
        }

    async def capture(request: Request, endpoint: str) -> dict[str, Any]:
        body = await request.json()
        active = store.get_active()
        number = store.next_sequence(active.run_id)
        raw_bytes = await request.body()
        record = CaptureRecord(
            run_id=active.run_id,
            request_number=number,
            endpoint=endpoint,
            raw_body_sha256=hashlib.sha256(raw_bytes).hexdigest(),
            body=body,
            extracted_tools=_extract_tools(body),
        )
        store.append_capture(record, redact(body))
        if endpoint == "/v1/chat/completions":
            return _canned_chat_response()
        return _canned_responses_api()

    @app.post("/v1/chat/completions")
    async def chat_completions(request: Request) -> dict[str, Any]:
        return await capture(request, "/v1/chat/completions")

    @app.post("/v1/responses")
    async def responses(request: Request) -> dict[str, Any]:
        return await capture(request, "/v1/responses")

    @app.post("/approvaltrace/activate")
    def activate(payload: ActivateScenarioRequest) -> dict[str, Any]:
        active = store.activate(payload.run_id, payload.scenario_id, payload.phase)
        return active.model_dump(mode="json")

    @app.post("/approvaltrace/phase/{phase}")
    def phase(phase: str) -> dict[str, Any]:
        if phase not in {"initial", "mutated"}:
            return {"error": "phase must be initial or mutated"}
        return store.set_phase(phase)

    @app.get("/approvaltrace/state")
    def state() -> dict[str, Any]:
        return store.read_server_state()

    @app.get("/approvaltrace/runs/{run_id}/captures")
    def captures(run_id: str) -> list[dict[str, Any]]:
        return store.list_captures(run_id)

    return app


app = create_app()
