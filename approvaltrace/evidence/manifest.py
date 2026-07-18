from __future__ import annotations

import json
from pathlib import Path

from approvaltrace.evidence.hashing import sha256_file

EXCLUDED = {"evidence-manifest.json", "evidence.sha256", "report.html"}


def build_manifest(run_dir: Path) -> dict[str, object]:
    files: list[dict[str, str]] = []
    for path in sorted(item for item in run_dir.rglob("*") if item.is_file()):
        relative = path.relative_to(run_dir).as_posix()
        if relative in EXCLUDED:
            continue
        files.append({"path": relative, "sha256": sha256_file(path)})
    return {"format": "approvaltrace-evidence-v1", "files": files}


def write_manifest(run_dir: Path) -> Path:
    manifest = build_manifest(run_dir)
    path = run_dir / "evidence-manifest.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    lines = [f"{item['sha256']}  {item['path']}" for item in manifest["files"]]  # type: ignore[index]
    (run_dir / "evidence.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def verify_manifest(run_dir: Path) -> list[str]:
    path = run_dir / "evidence-manifest.json"
    if not path.exists():
        return ["missing evidence-manifest.json"]
    manifest = json.loads(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    for item in manifest.get("files", []):
        file_path = run_dir / item["path"]
        if not file_path.exists():
            errors.append(f"missing {item['path']}")
            continue
        actual = sha256_file(file_path)
        if actual != item["sha256"]:
            errors.append(f"hash mismatch {item['path']}")
    return errors
