from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
import uvicorn

from approvaltrace.automation.protocol import SCENARIOS
from approvaltrace.capture_api.app import create_app
from approvaltrace.evidence.manifest import verify_manifest, write_manifest
from approvaltrace.evidence.report import generate_report

app = typer.Typer(help="MCP ApprovalTrace research harness")
automate_app = typer.Typer(help="Run automated client experiments")
app.add_typer(automate_app, name="automate")


@app.command("capture-api")
def capture_api(
    host: Annotated[str, typer.Option()] = "127.0.0.1",
    port: Annotated[int, typer.Option()] = 8741,
    root: Annotated[Path, typer.Option()] = Path(".approvaltrace"),
) -> None:
    """Run the local OpenAI-compatible model request capture service."""
    uvicorn.run(create_app(root), host=host, port=port)


@app.command("verify")
def verify(run_dir: Path) -> None:
    """Verify all hashes in a published evidence bundle."""
    errors = verify_manifest(run_dir)
    if errors:
        for error in errors:
            typer.echo(f"FAIL: {error}")
        raise typer.Exit(code=1)
    typer.echo("PASS: evidence bundle hashes are valid")


@app.command("manifest")
def manifest(run_dir: Path) -> None:
    path = write_manifest(run_dir)
    typer.echo(str(path))


@app.command("report")
def report(run_dir: Path) -> None:
    path = generate_report(run_dir)
    typer.echo(str(path))


@app.command("show")
def show(path: Path) -> None:
    """Pretty-print a JSON evidence file."""
    value = json.loads(path.read_text(encoding="utf-8"))
    typer.echo(json.dumps(value, indent=2, ensure_ascii=False))


@automate_app.command("cline")
def automate_cline(
    root: Annotated[Path, typer.Option(help="Private automation output root")] = Path(
        ".approvaltrace"
    ),
    editor_exe: Annotated[
        Path,
        typer.Option(help="Path to Visual Studio Code Code.exe"),
    ] = Path(r"C:\Users\Alex\AppData\Local\Programs\Microsoft VS Code\Code.exe"),
    cline_extension: Annotated[
        Path,
        typer.Option(help="Path to the installed Cline extension directory"),
    ] = Path(r"C:\Users\Alex\.vscode\extensions\saoudrizwan.claude-dev-4.0.9"),
    scenario: Annotated[
        list[str] | None,
        typer.Option(help="Scenario ID to run; repeat for more than one"),
    ] = None,
) -> None:
    """Run Cline against isolated profiles and generate a batch report."""
    try:
        from approvaltrace.automation.runner import AutomatedClineBatch
    except ImportError as exc:
        raise typer.BadParameter(
            'Cline automation requires: python -m pip install -e ".[automation]"'
        ) from exc
    repo = Path.cwd().resolve()
    selected = tuple(
        item for item in SCENARIOS if not scenario or item.scenario_id in set(scenario)
    )
    unknown = set(scenario or []) - {item.scenario_id for item in SCENARIOS}
    if unknown:
        raise typer.BadParameter(f"Unknown scenario IDs: {', '.join(sorted(unknown))}")
    if not selected:
        raise typer.BadParameter("No scenarios selected")
    for path, label in ((editor_exe, "editor"), (cline_extension, "Cline extension")):
        if not path.exists():
            raise typer.BadParameter(f"{label} path does not exist: {path}")
    runner = AutomatedClineBatch(
        repo=repo,
        root=root,
        editor_exe=editor_exe,
        cline_extension=cline_extension,
        scenarios=selected,
    )
    batch_dir = runner.run()
    typer.echo(str(batch_dir / "report.html"))


if __name__ == "__main__":
    app()
