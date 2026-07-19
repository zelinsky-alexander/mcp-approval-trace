from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScenarioProtocol:
    scenario_id: str
    prompt: str
    mutation: bool = False
    notification_expected: bool | None = None
    marker: str | None = None
    wait_after_mutation_seconds: float = 0.0
    try_new_task_before_reconnect: bool = False


SCENARIOS: tuple[ScenarioProtocol, ...] = (
    ScenarioProtocol(
        scenario_id="AT-001",
        prompt="List the available test tools. Do not call them.",
    ),
    ScenarioProtocol(
        scenario_id="AT-002",
        prompt="List the available test tools. Do not call them.",
        marker="APPROVALTRACE_TAG_MARKER",
    ),
    ScenarioProtocol(
        scenario_id="AT-003",
        prompt="List the available test tools and their parameters. Do not call them.",
        marker="NESTED_FIELD_PRESENT",
    ),
    ScenarioProtocol(
        scenario_id="AT-004",
        prompt="List the available test tools and parameters. Do not call them.",
        mutation=True,
        notification_expected=True,
        marker="export_target",
    ),
    ScenarioProtocol(
        scenario_id="AT-005",
        prompt="List the available test tools. Do not call them.",
        mutation=True,
        notification_expected=True,
        marker="APPROVALTRACE_MUTATED",
    ),
    ScenarioProtocol(
        scenario_id="AT-006",
        prompt="List the available test tools. Do not call them.",
        mutation=True,
        notification_expected=False,
        marker="APPROVALTRACE_SILENT_MUTATION",
        wait_after_mutation_seconds=5.0,
        try_new_task_before_reconnect=True,
    ),
)


def scenario_protocol(scenario_id: str) -> ScenarioProtocol:
    for protocol in SCENARIOS:
        if protocol.scenario_id == scenario_id:
            return protocol
    raise KeyError(f"Unknown scenario protocol: {scenario_id}")
