from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class CaptureRecord(BaseModel):
    run_id: str
    request_number: int = Field(ge=1)
    received_at: datetime = Field(default_factory=utc_now)
    endpoint: str
    raw_body_sha256: str
    body: dict[str, Any]
    extracted_tools: list[dict[str, Any]] = Field(default_factory=list)


class ActiveRun(BaseModel):
    run_id: str = "default"
    scenario_id: str = "AT-001"
    created_at: datetime = Field(default_factory=utc_now)


class ActivateScenarioRequest(BaseModel):
    run_id: str
    scenario_id: str
    phase: str = Field(default="initial", pattern="^(initial|mutated)$")


class CannedModelResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str = "approvaltrace-capture"
    choices: list[dict[str, Any]]
