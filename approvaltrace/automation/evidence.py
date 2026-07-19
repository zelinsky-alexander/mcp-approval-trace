from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import yaml

from approvaltrace.analyzer.compare import (
    analyze_text_fields,
    compare_model_to_observation,
    compare_server_to_model,
    dataclasses_as_dicts,
)
from approvaltrace.automation.cline_extract import extract_model_tool
from approvaltrace.evidence.manifest import write_manifest
from approvaltrace.evidence.report import generate_report


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )


def build_run_evidence(
    *,
    run_dir: Path,
    scenario_file: Path,
    initial_tool: dict[str, Any],
    mutated_tool: dict[str, Any] | None,
    captures: list[dict[str, Any]],
    ui_observation: dict[str, Any],
    environment: dict[str, Any],
    timeline: list[dict[str, Any]],
    findings: dict[str, Any],
) -> tuple[str, bool]:
    run_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(scenario_file, run_dir / "scenario.yaml")
    write_json(run_dir / "environment.json", environment)
    write_json(run_dir / "server-tool.initial.json", initial_tool)
    if mutated_tool is not None:
        write_json(run_dir / "server-tool.mutated.json", mutated_tool)
    write_json(run_dir / "ui-observation.json", ui_observation)
    write_json(run_dir / "event-timeline.json", timeline)

    model_representations: list[dict[str, Any]] = []
    comparison: list[dict[str, Any]] = []
    approval_comparison: list[dict[str, Any]] = []
    codepoints: list[dict[str, Any]] = []
    extraction_methods: set[str] = set()
    for capture in captures:
        body = capture.get("body", {})
        model_tool, method = extract_model_tool(
            body, server_name="approvaltrace", tool_name=initial_tool["name"]
        )
        extraction_methods.add(method)
        model_representations.append(
            {
                "request_number": capture.get("request_number"),
                "phase": capture.get("phase"),
                "extraction_method": method,
                "tool": model_tool,
            }
        )
        if model_tool is None:
            continue
        expected_tool = (
            mutated_tool if capture.get("phase") == "mutated" and mutated_tool else initial_tool
        )
        comparison.extend(
            {
                "request_number": capture.get("request_number"),
                **item,
            }
            for item in dataclasses_as_dicts(compare_server_to_model(expected_tool, model_tool))
        )
        visible_fields = ui_observation.get("visible_fields", {})
        approval_comparison.extend(
            {
                "request_number": capture.get("request_number"),
                **item,
            }
            for item in dataclasses_as_dicts(
                compare_model_to_observation(model_tool, visible_fields)
            )
        )
        codepoints.extend(
            {"request_number": capture.get("request_number"), **item}
            for item in analyze_text_fields(model_tool)
        )

    write_json(run_dir / "model-representations.json", model_representations)
    write_json(run_dir / "field-comparison.json", comparison)
    write_json(run_dir / "approval-comparison.json", approval_comparison)
    write_json(run_dir / "codepoints.json", codepoints)
    write_json(run_dir / "findings.json", findings)
    observer = {
        "run_id": environment["run_id"],
        "client": {
            "name": environment["client_name"],
            "version": environment["client_version"],
            "operating_system": environment["operating_system"],
            "configuration_hash": environment.get("configuration_hash"),
        },
        "approval": {
            "shown": ui_observation.get("approval_shown"),
            "screenshot": "approval-before.png",
            "visible_fields": ui_observation.get("visible_fields", {}),
            "description_text_copied": ui_observation.get("description_text"),
        },
        "mutation": {
            "warning_shown": ui_observation.get("warning_shown"),
            "new_approval_shown": ui_observation.get("new_approval_shown"),
            "visible_diff_shown": ui_observation.get("visible_diff_shown"),
            "changed_requests_before_reapproval": findings.get(
                "changed_requests_before_reapproval", 0
            ),
        },
        "notes": " ".join(ui_observation.get("notes", [])) or None,
    }
    (run_dir / "observer.yaml").write_text(
        yaml.safe_dump(observer, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    generate_report(run_dir)
    write_manifest(run_dir)

    method = next(iter(extraction_methods)) if len(extraction_methods) == 1 else "mixed"
    evidence_complete = bool(
        captures
        and model_representations
        and method != "unsupported"
        and (run_dir / "approval-before.png").exists()
    )
    return method, evidence_complete
