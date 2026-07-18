from __future__ import annotations

import base64
import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from approvaltrace.analyzer.codepoints import encode_tag_text


def scenario_dir() -> Path:
    configured = os.environ.get("APPROVALTRACE_SCENARIO_DIR")
    return Path(configured) if configured else Path(__file__).parent / "scenarios"


def load_scenario(scenario_id: str) -> dict[str, Any]:
    matches = list(scenario_dir().glob(f"{scenario_id}-*.yaml"))
    if not matches:
        raise FileNotFoundError(f"Scenario not found: {scenario_id}")
    return yaml.safe_load(matches[0].read_text(encoding="utf-8"))


def _expand_special_values(value: Any) -> Any:
    if isinstance(value, dict):
        if set(value) == {"tag_text"}:
            return encode_tag_text(str(value["tag_text"]))
        if set(value) == {"utf8_base64"}:
            return base64.b64decode(value["utf8_base64"]).decode("utf-8")
        if set(value) == {"concat"}:
            return "".join(str(_expand_special_values(item)) for item in value["concat"])
        return {key: _expand_special_values(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_expand_special_values(item) for item in value]
    return value


def deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def tool_for_phase(scenario: dict[str, Any], phase: str) -> dict[str, Any]:
    initial = _expand_special_values(scenario["initial"]["tool"])
    if phase == "initial" or not scenario.get("mutation"):
        return initial
    changes = _expand_special_values(scenario["mutation"].get("changes", {}).get("tool", {}))
    tool = deep_merge(initial, changes)
    append_description = scenario["mutation"].get("append_description")
    if append_description is not None:
        tool["description"] = str(tool.get("description", "")) + str(
            _expand_special_values(append_description)
        )
    return tool


def scenario_summary(scenario: dict[str, Any]) -> str:
    return json.dumps(
        {
            "id": scenario["id"],
            "title": scenario["title"],
            "category": scenario["category"],
        },
        sort_keys=True,
    )
