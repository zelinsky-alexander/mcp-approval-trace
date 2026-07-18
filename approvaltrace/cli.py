from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
import uvicorn

from approvaltrace.capture_api.app import create_app
from approvaltrace.evidence.manifest import verify_manifest, write_manifest
from approvaltrace.evidence.report import generate_report

app = typer.Typer(help="MCP ApprovalTrace research harness")


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


if __name__ == "__main__":
    app()
