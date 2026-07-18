from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def state_file() -> Path:
    return Path(os.environ.get("APPROVALTRACE_STATE_FILE", ".approvaltrace/server-state.json"))


def read_state() -> dict[str, Any]:
    path = state_file()
    if not path.exists():
        return {"run_id": "default", "scenario_id": "AT-001", "phase": "initial"}
    return json.loads(path.read_text(encoding="utf-8"))
