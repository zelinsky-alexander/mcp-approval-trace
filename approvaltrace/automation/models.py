from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class TimelineEvent:
    timestamp: str
    event: str
    phase: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class UiObservation:
    source: str = "playwright_visible_dom"
    approval_shown: bool | None = None
    warning_shown: bool | None = None
    notification_shown: bool | None = None
    new_approval_shown: bool | None = None
    visible_diff_shown: bool | None = None
    tool_list_refreshed: bool | None = None
    forced_reconnect: bool = False
    visible_fields: dict[str, str] = field(default_factory=dict)
    visible_text: str = ""
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ScenarioResult:
    run_id: str
    scenario_id: str
    title: str
    result: str
    severity: str
    reasons: list[str]
    capture_count: int
    changed_requests_before_reapproval: int
    model_extraction: str
    evidence_complete: bool
    notification_expected: bool | None = None
    notification_observed: bool | None = None
    automatic_refresh: bool | None = None
    reapproval_observed: bool | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
