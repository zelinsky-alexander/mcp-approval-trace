from __future__ import annotations

import json
import re
from typing import Any

SERVER_HEADING = re.compile(r"^## (?P<name>[^\r\n(]+?)(?:\s+\([^\r\n]*\))?\s*$", re.MULTILINE)
TOOL_LINE = re.compile(r"^- (?P<name>[A-Za-z0-9_.:-]+):\s*(?P<description>.*)$", re.MULTILINE)
SCHEMA_LABEL = re.compile(r"^\s*Input Schema:\s*$", re.MULTILINE)


def _system_text(body: dict[str, Any]) -> str:
    parts: list[str] = []
    for message in body.get("messages", []):
        if not isinstance(message, dict) or message.get("role") != "system":
            continue
        content = message.get("content")
        if isinstance(content, str):
            parts.append(content)
    return "\n".join(parts)


def extract_cline_mcp_tool(
    body: dict[str, Any], *, server_name: str, tool_name: str
) -> dict[str, Any] | None:
    """Extract a tool deterministically from Cline's model-bound system prompt."""
    text = _system_text(body)
    server_match = next(
        (match for match in SERVER_HEADING.finditer(text) if match.group("name") == server_name),
        None,
    )
    if server_match is None:
        return None
    section_end = text.find("\n====", server_match.end())
    section = text[server_match.end() : section_end if section_end >= 0 else len(text)]
    tool_match = next(
        (match for match in TOOL_LINE.finditer(section) if match.group("name") == tool_name),
        None,
    )
    if tool_match is None:
        return None
    schema_label = SCHEMA_LABEL.search(section, tool_match.end())
    if schema_label is None:
        return None
    json_start = section.find("{", schema_label.end())
    if json_start < 0:
        return None
    try:
        schema, _ = json.JSONDecoder().raw_decode(section[json_start:])
    except json.JSONDecodeError:
        return None
    if not isinstance(schema, dict):
        return None
    return {
        "name": tool_match.group("name"),
        "description": tool_match.group("description"),
        "inputSchema": schema,
    }


def extract_model_tool(
    body: dict[str, Any], *, server_name: str, tool_name: str
) -> tuple[dict[str, Any] | None, str]:
    for entry in body.get("tools", []):
        if not isinstance(entry, dict):
            continue
        candidate = entry.get("function", entry)
        if isinstance(candidate, dict) and candidate.get("name") == tool_name:
            normalized = dict(candidate)
            if "inputSchema" not in normalized and isinstance(normalized.get("parameters"), dict):
                normalized["inputSchema"] = normalized.pop("parameters")
            return normalized, "openai_tools"
    tool = extract_cline_mcp_tool(body, server_name=server_name, tool_name=tool_name)
    return tool, "cline_system_prompt" if tool is not None else "unsupported"
