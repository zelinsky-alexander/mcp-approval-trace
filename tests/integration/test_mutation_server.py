from __future__ import annotations

import json
import os
import select
import subprocess
import sys
import time
from pathlib import Path


def _read_json_line(process: subprocess.Popen[str], timeout: float = 3.0) -> dict:
    assert process.stdout is not None
    ready, _, _ = select.select([process.stdout], [], [], timeout)
    assert ready, "timed out waiting for MCP server response"
    return json.loads(process.stdout.readline())


def _send(process: subprocess.Popen[str], message: dict) -> None:
    assert process.stdin is not None
    process.stdin.write(json.dumps(message) + "\n")
    process.stdin.flush()


def _start_server(tmp_path: Path, scenario_id: str) -> tuple[subprocess.Popen[str], Path]:
    root = Path(__file__).parents[2]
    state = tmp_path / "server-state.json"
    state.write_text(
        json.dumps({"run_id": "test", "scenario_id": scenario_id, "phase": "initial"}),
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root)
    env["APPROVALTRACE_STATE_FILE"] = str(state)
    env["APPROVALTRACE_SCENARIO_DIR"] = str(root / "mutation_server" / "scenarios")
    process = subprocess.Popen(
        [sys.executable, "-m", "mutation_server.server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    return process, state


def test_clean_tools_list(tmp_path: Path) -> None:
    process, _ = _start_server(tmp_path, "AT-001")
    try:
        _send(process, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        initialize = _read_json_line(process)
        assert initialize["result"]["serverInfo"]["name"] == "mcp-approval-trace"

        _send(process, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        _send(process, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        tools = _read_json_line(process)
        assert tools["result"]["tools"][0]["name"] == "search_test_documents"
    finally:
        process.terminate()
        process.wait(timeout=3)


def test_notified_mutation_emits_list_changed(tmp_path: Path) -> None:
    process, state = _start_server(tmp_path, "AT-005")
    try:
        _send(process, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        _read_json_line(process)
        _send(process, {"jsonrpc": "2.0", "method": "notifications/initialized"})

        state.write_text(
            json.dumps({"run_id": "test", "scenario_id": "AT-005", "phase": "mutated"}),
            encoding="utf-8",
        )
        notification = _read_json_line(process, timeout=4)
        assert notification["method"] == "notifications/tools/list_changed"

        _send(process, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        tools = _read_json_line(process)
        assert "APPROVALTRACE_MUTATED" in tools["result"]["tools"][0]["description"]
    finally:
        process.terminate()
        process.wait(timeout=3)


def test_silent_mutation_does_not_emit_notification(tmp_path: Path) -> None:
    process, state = _start_server(tmp_path, "AT-006")
    try:
        _send(process, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        _read_json_line(process)
        _send(process, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        state.write_text(
            json.dumps({"run_id": "test", "scenario_id": "AT-006", "phase": "mutated"}),
            encoding="utf-8",
        )
        time.sleep(0.5)
        assert process.stdout is not None
        ready, _, _ = select.select([process.stdout], [], [], 0.2)
        assert not ready

        _send(process, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        tools = _read_json_line(process)
        assert "APPROVALTRACE_SILENT_MUTATION" in tools["result"]["tools"][0]["description"]
    finally:
        process.terminate()
        process.wait(timeout=3)
