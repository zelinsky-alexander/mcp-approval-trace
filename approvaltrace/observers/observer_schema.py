from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Visibility = Literal[
    "full",
    "partial",
    "truncated",
    "absent",
    "not_applicable",
    "unable_to_determine",
]


class ClientObservation(BaseModel):
    name: str
    version: str
    operating_system: str
    configuration_hash: str | None = None


class ApprovalObservation(BaseModel):
    shown: bool | None = None
    screenshot: str | None = None
    visible_fields: dict[str, Visibility] = Field(default_factory=dict)
    description_text_copied: str | None = None


class MutationObservation(BaseModel):
    warning_shown: bool | None = None
    new_approval_shown: bool | None = None
    visible_diff_shown: bool | None = None
    changed_requests_before_reapproval: int = Field(default=0, ge=0)


class ObserverRecord(BaseModel):
    run_id: str
    client: ClientObservation
    approval: ApprovalObservation
    mutation: MutationObservation = Field(default_factory=MutationObservation)
    notes: str | None = None
