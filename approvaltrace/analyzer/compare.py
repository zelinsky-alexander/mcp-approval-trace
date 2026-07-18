from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from approvaltrace.analyzer.codepoints import findings_as_dicts
from approvaltrace.analyzer.schema_paths import flatten_tool


@dataclass(frozen=True)
class FieldDelta:
    path: str
    server_value: Any
    model_value: Any
    status: str


@dataclass(frozen=True)
class ApprovalFinding:
    path: str
    model_value: Any
    visibility: str
    status: str


def compare_server_to_model(
    server_tool: dict[str, Any], model_tool: dict[str, Any]
) -> list[FieldDelta]:
    server = flatten_tool(server_tool)
    model = flatten_tool(model_tool)
    paths = sorted(set(server) | set(model))
    deltas: list[FieldDelta] = []
    for path in paths:
        left = server.get(path)
        right = model.get(path)
        status = "match" if left == right else "different"
        if path not in server:
            status = "model_only"
        elif path not in model:
            status = "server_only"
        deltas.append(FieldDelta(path, left, right, status))
    return deltas


def compare_model_to_observation(
    model_tool: dict[str, Any], visible_fields: dict[str, str]
) -> list[ApprovalFinding]:
    flattened = flatten_tool(model_tool)
    results: list[ApprovalFinding] = []
    for path, value in flattened.items():
        root = path.split(".", 1)[0]
        if root == "inputSchema":
            key = "input_schema"
        elif root == "outputSchema":
            key = "output_schema"
        elif root == "_meta":
            key = "meta"
        elif root == "name":
            key = "tool_name"
        elif root == "description":
            key = "tool_description"
        else:
            key = root.lower()
        visibility = visible_fields.get(key, "unable_to_determine")
        status = "represented" if visibility == "full" else "not_fully_represented"
        results.append(ApprovalFinding(path, value, visibility, status))
    return results


def analyze_text_fields(tool: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for path, value in flatten_tool(tool).items():
        if isinstance(value, str):
            for item in findings_as_dicts(value):
                findings.append({"path": path, **item})
    return findings


def dataclasses_as_dicts(items: list[Any]) -> list[dict[str, Any]]:
    return [asdict(item) for item in items]
