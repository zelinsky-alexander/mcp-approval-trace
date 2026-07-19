from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


def _value(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    return str(value)


def _status_class(result: str) -> str:
    return {
        "PASS": "pass",
        "PARTIAL": "partial",
        "FAIL": "fail",
        "INCONCLUSIVE": "inconclusive",
    }.get(result, "inconclusive")


def generate_batch_dashboard(batch_dir: Path, summary: dict[str, Any]) -> Path:
    rows: list[str] = []
    timelines: list[str] = []
    for result in summary.get("results", []):
        scenario_id = html.escape(str(result.get("scenario_id", "")))
        run_id = html.escape(str(result.get("run_id", "")))
        outcome = html.escape(str(result.get("result", "INCONCLUSIVE")))
        report_href = html.escape(f"runs/{run_id}/report.html", quote=True)
        rows.append(
            "<tr>"
            f"<th scope='row'><a href='{report_href}'>{scenario_id}</a></th>"
            f"<td><span class='status {_status_class(outcome)}'>{outcome}</span></td>"
            f"<td>{html.escape(_value(result.get('model_extraction')))}</td>"
            f"<td>{html.escape(_value(result.get('notification_observed')))}</td>"
            f"<td>{html.escape(_value(result.get('automatic_refresh')))}</td>"
            f"<td>{html.escape(_value(result.get('reapproval_observed')))}</td>"
            f"<td>{html.escape(_value(result.get('changed_requests_before_reapproval')))}</td>"
            f"<td>{html.escape(_value(result.get('evidence_complete')))}</td>"
            "</tr>"
        )
        timeline_path = batch_dir / "runs" / str(result.get("run_id")) / "event-timeline.json"
        if timeline_path.exists():
            events = json.loads(timeline_path.read_text(encoding="utf-8"))
            event_items = "".join(
                "<li>"
                f"<time>{html.escape(str(event.get('timestamp', '')))}</time>"
                f"<strong>{html.escape(str(event.get('event', '')))}</strong>"
                f"<span>{html.escape(str(event.get('phase', '')))}</span>"
                "</li>"
                for event in events
            )
            timelines.append(
                f"<details><summary>{scenario_id} timeline</summary>"
                f"<ol>{event_items}</ol></details>"
            )

    generated_at = html.escape(str(summary.get("generated_at", "")))
    client = html.escape(str(summary.get("client", "Cline")))
    body = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MCP ApprovalTrace batch results</title>
<style>
:root {{ color-scheme: light dark; font-family: system-ui, sans-serif; }}
body {{ max-width: 1280px; margin: 2rem auto; padding: 0 1rem; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border-bottom: 1px solid CanvasText; padding: .65rem; text-align: left; }}
thead th {{ position: sticky; top: 0; background: Canvas; }}
.status {{
  display: inline-block; border: 1px solid currentColor;
  border-radius: 999px; padding: .1rem .5rem;
}}
.pass {{ color: #16803c; }} .partial {{ color: #946200; }}
.fail {{ color: #c62828; }} .inconclusive {{ color: #666; }}
details {{ margin: 1rem 0; }}
ol {{ display: flex; flex-wrap: wrap; gap: .75rem; list-style: none; padding: 0; }}
li {{ border-left: .25rem solid currentColor; padding: .4rem .7rem; min-width: 12rem; }}
li time, li span {{ display: block; opacity: .75; font-size: .85rem; }}
@media (max-width: 760px) {{ table {{ display: block; overflow-x: auto; }} }}
</style>
</head>
<body>
<h1>MCP ApprovalTrace batch results</h1>
<p>Client: <strong>{client}</strong> · Generated: {generated_at}</p>
<table>
<thead><tr>
<th>Scenario</th><th>Result</th><th>M extraction</th><th>Notification</th>
<th>Auto refresh</th><th>Reapproval</th>
<th>Changed requests before reapproval</th><th>Evidence complete</th>
</tr></thead>
<tbody>{"".join(rows)}</tbody>
</table>
<h2>Event timelines</h2>
{"".join(timelines)}
</body>
</html>
"""
    path = batch_dir / "report.html"
    path.write_text(body, encoding="utf-8")
    return path
