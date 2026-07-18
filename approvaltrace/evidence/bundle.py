from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from approvaltrace.analyzer.compare import (
    analyze_text_fields,
    compare_server_to_model,
    dataclasses_as_dicts,
)
from approvaltrace.evidence.manifest import write_manifest
from approvaltrace.evidence.report import generate_report


def _extract_model_tool(body: dict[str, Any], tool_name: str) -> dict[str, Any] | None:
    for entry in body.get("tools", []):
        if not isinstance(entry, dict):
            continue
        candidate = entry.get("function", entry)
        if isinstance(candidate, dict) and candidate.get("name") == tool_name:
            return candidate
    return None


def finalize_bundle(
    *,
    run_dir: Path,
    scenario_file: Path,
    server_tool: dict[str, Any],
    model_body: dict[str, Any],
    findings: dict[str, Any],
) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(scenario_file, run_dir / "scenario.yaml")
    (run_dir / "server-tool.json").write_text(
        json.dumps(server_tool, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    (run_dir / "model-request.redacted.json").write_text(
        json.dumps(model_body, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    model_tool = _extract_model_tool(model_body, server_tool["name"])
    if model_tool is None:
        deltas = []
    else:
        deltas = dataclasses_as_dicts(compare_server_to_model(server_tool, model_tool))
    unicode_findings = [] if model_tool is None else analyze_text_fields(model_tool)
    (run_dir / "field-comparison.json").write_text(
        json.dumps(deltas, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (run_dir / "codepoints.json").write_text(
        json.dumps(unicode_findings, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (run_dir / "findings.json").write_text(
        json.dumps(findings, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    write_manifest(run_dir)
    return generate_report(run_dir)
