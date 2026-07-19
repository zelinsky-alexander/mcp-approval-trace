from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any

from approvaltrace.capture_api.models import ActiveRun, CaptureRecord


class CaptureStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    @property
    def active_file(self) -> Path:
        return self.root / "active-run.json"

    def get_active(self) -> ActiveRun:
        if not self.active_file.exists():
            active = ActiveRun()
            self.set_active(active)
            return active
        return ActiveRun.model_validate_json(self.active_file.read_text(encoding="utf-8"))

    def set_active(self, active: ActiveRun) -> None:
        self.active_file.write_text(active.model_dump_json(indent=2), encoding="utf-8")
        self._write_server_state(active.run_id, active.scenario_id, "initial")

    def activate(self, run_id: str, scenario_id: str, phase: str) -> ActiveRun:
        active = ActiveRun(run_id=run_id, scenario_id=scenario_id)
        self.active_file.write_text(active.model_dump_json(indent=2), encoding="utf-8")
        self._write_server_state(run_id, scenario_id, phase)
        return active

    def set_phase(self, phase: str) -> dict[str, Any]:
        active = self.get_active()
        self._write_server_state(active.run_id, active.scenario_id, phase)
        return self.read_server_state()

    def _write_server_state(self, run_id: str, scenario_id: str, phase: str) -> None:
        state = {"run_id": run_id, "scenario_id": scenario_id, "phase": phase}
        (self.root / "server-state.json").write_text(
            json.dumps(state, indent=2, sort_keys=True), encoding="utf-8"
        )

    def read_server_state(self) -> dict[str, Any]:
        path = self.root / "server-state.json"
        if not path.exists():
            active = self.get_active()
            self._write_server_state(active.run_id, active.scenario_id, "initial")
        return json.loads(path.read_text(encoding="utf-8"))

    def append_capture(self, record: CaptureRecord, redacted_body: dict[str, Any]) -> None:
        run_dir = self.root / "runs" / record.run_id / "captures"
        run_dir.mkdir(parents=True, exist_ok=True)
        stem = f"model-request-{record.request_number:03d}"
        with self._lock:
            (run_dir / f"{stem}.raw.json").write_text(
                json.dumps(record.body, ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            (run_dir / f"{stem}.redacted.json").write_text(
                json.dumps(redacted_body, ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            with (run_dir / "captures.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(record.model_dump_json() + "\n")

    def next_sequence(self, run_id: str) -> int:
        path = self.root / "runs" / run_id / "captures" / "captures.jsonl"
        if not path.exists():
            return 1
        with path.open("r", encoding="utf-8") as handle:
            return sum(1 for line in handle if line.strip()) + 1

    def list_captures(self, run_id: str) -> list[dict[str, Any]]:
        path = self.root / "runs" / run_id / "captures" / "captures.jsonl"
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
