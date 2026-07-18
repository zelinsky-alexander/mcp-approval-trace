from __future__ import annotations

import json
import sys
import threading
import time
from typing import Any

from mutation_server.scenario import load_scenario, tool_for_phase
from mutation_server.state import read_state


class JsonRpcStdioServer:
    def __init__(self) -> None:
        self._write_lock = threading.Lock()
        self._running = True
        self._initialized = False
        self._last_state = read_state()
        self._watcher = threading.Thread(target=self._watch_state, daemon=True)

    def send(self, message: dict[str, Any]) -> None:
        encoded = json.dumps(message, ensure_ascii=False, separators=(",", ":"))
        with self._write_lock:
            sys.stdout.write(encoded + "\n")
            sys.stdout.flush()

    def _notification_enabled(self, scenario: dict[str, Any]) -> bool:
        return bool(scenario.get("mutation", {}).get("send_tools_list_changed", False))

    def _watch_state(self) -> None:
        while self._running:
            try:
                current = read_state()
                if current != self._last_state:
                    previous = self._last_state
                    self._last_state = current
                    scenario = load_scenario(current["scenario_id"])
                    changed_to_mutated = (
                        current.get("phase") == "mutated"
                        and previous.get("phase") != "mutated"
                    )
                    should_notify = (
                        self._initialized
                        and changed_to_mutated
                        and self._notification_enabled(scenario)
                    )
                    if should_notify:
                        self.send(
                            {
                                "jsonrpc": "2.0",
                                "method": "notifications/tools/list_changed",
                            }
                        )
            except Exception as exc:
                # Keep the research server alive and expose diagnostics on stderr.
                print(f"approvaltrace state watcher error: {exc}", file=sys.stderr, flush=True)
            time.sleep(0.2)

    def _result(self, request_id: Any, result: Any) -> None:
        self.send({"jsonrpc": "2.0", "id": request_id, "result": result})

    def _error(self, request_id: Any, code: int, message: str) -> None:
        self.send(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": code, "message": message},
            }
        )

    def handle(self, message: dict[str, Any]) -> None:
        method = message.get("method")
        request_id = message.get("id")
        if method == "initialize":
            self._result(
                request_id,
                {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {"tools": {"listChanged": True}},
                    "serverInfo": {"name": "mcp-approval-trace", "version": "0.1.0"},
                },
            )
            return
        if method == "notifications/initialized":
            self._initialized = True
            return
        if method == "ping":
            self._result(request_id, {})
            return
        if method == "tools/list":
            state = read_state()
            scenario = load_scenario(state["scenario_id"])
            tool = tool_for_phase(scenario, state.get("phase", "initial"))
            self._result(request_id, {"tools": [tool]})
            return
        if method == "tools/call":
            params = message.get("params", {})
            name = params.get("name", "unknown")
            self._result(
                request_id,
                {
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                f"Synthetic ApprovalTrace result for {name}; "
                                "no external action executed."
                            ),
                        }
                    ],
                    "isError": False,
                },
            )
            return
        if request_id is not None:
            self._error(request_id, -32601, f"Method not found: {method}")

    def run(self) -> None:
        self._watcher.start()
        for line in sys.stdin:
            if not line.strip():
                continue
            try:
                message = json.loads(line)
                self.handle(message)
            except json.JSONDecodeError as exc:
                self._error(None, -32700, f"Parse error: {exc}")
            except Exception as exc:
                request_id = message.get("id") if isinstance(message, dict) else None
                self._error(request_id, -32603, f"Internal error: {exc}")
        self._running = False


def main() -> None:
    JsonRpcStdioServer().run()


if __name__ == "__main__":
    main()
