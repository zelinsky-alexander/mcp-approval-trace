from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def generate_report(run_dir: Path) -> Path:
    findings = _read_json(run_dir / "findings.json") or {}
    comparison = _read_json(run_dir / "field-comparison.json") or []
    scenario_path = run_dir / "scenario.yaml"
    scenario = scenario_path.read_text(encoding="utf-8") if scenario_path.exists() else ""
    findings_json = html.escape(json.dumps(findings, indent=2, ensure_ascii=False))
    comparison_json = html.escape(json.dumps(comparison, indent=2, ensure_ascii=False))
    scenario_html = html.escape(scenario)
    verify_command = html.escape(str(run_dir))
    body = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>MCP ApprovalTrace report</title>
<style>
body {{ font-family: system-ui; max-width: 1100px; margin: 2rem auto; padding: 0 1rem; }}
pre {{ background: #f4f4f4; padding: 1rem; overflow: auto; }}
table {{ border-collapse: collapse; width: 100%; }}
td, th {{ border: 1px solid #ccc; padding: .45rem; text-align: left; }}
</style>
</head>
<body>
<h1>MCP ApprovalTrace evidence report</h1>
<h2>Finding</h2><pre>{findings_json}</pre>
<h2>Field comparison</h2><pre>{comparison_json}</pre>
<h2>Scenario</h2><pre>{scenario_html}</pre>
<p>Verify this bundle with <code>approvaltrace verify {verify_command}</code>.</p>
</body>
</html>
"""
    path = run_dir / "report.html"
    path.write_text(body, encoding="utf-8")
    return path
