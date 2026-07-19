from __future__ import annotations

from collections.abc import Iterator
from typing import Any

SECURITY_RELEVANT_ROOTS = {
    "name",
    "title",
    "description",
    "inputSchema",
    "outputSchema",
    "annotations",
    "execution",
    "_meta",
}


def iter_paths(value: Any, prefix: str = "") -> Iterator[tuple[str, Any]]:
    if isinstance(value, dict):
        for key in sorted(value):
            path = f"{prefix}.{key}" if prefix else key
            yield from iter_paths(value[key], path)
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            yield from iter_paths(item, f"{prefix}[{index}]")
        return
    yield prefix, value


def flatten_tool(tool: dict[str, Any]) -> dict[str, Any]:
    filtered = {key: value for key, value in tool.items() if key in SECURITY_RELEVANT_ROOTS}
    return dict(iter_paths(filtered))
