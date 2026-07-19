from __future__ import annotations

import hashlib
import json
import platform
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from approvaltrace.analyzer.codepoints import decode_tag_text
from approvaltrace.analyzer.findings import classify_run
from approvaltrace.automation.cline_extract import extract_model_tool
from approvaltrace.automation.dashboard import generate_batch_dashboard
from approvaltrace.automation.evidence import build_run_evidence, write_json
from approvaltrace.automation.models import ScenarioResult, TimelineEvent, UiObservation
from approvaltrace.automation.playwright_driver import (
    ClinePlaywrightDriver,
    seed_isolated_profile,
)
from approvaltrace.automation.protocol import SCENARIOS, ScenarioProtocol
from mutation_server.scenario import load_scenario, tool_for_phase


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _http_json(url: str, *, payload: dict[str, Any] | None = None) -> Any:
    body = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(
        url,
        data=body,
        method="GET" if body is None else "POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode())


def _wait_for_capture(base_url: str, run_id: str, count: int, timeout: float = 30) -> list[dict]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        captures = _http_json(f"{base_url}/approvaltrace/runs/{run_id}/captures")
        if len(captures) >= count:
            return captures
        time.sleep(0.25)
    raise TimeoutError(f"Timed out waiting for capture {count} for {run_id}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_sha(repo: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=False
    )
    return result.stdout.strip() or "unknown"


class CaptureApiProcess:
    def __init__(self, *, root: Path, port: int, log_dir: Path) -> None:
        self.root = root
        self.port = port
        self.log_dir = log_dir
        self.process: subprocess.Popen[str] | None = None
        self.stdout_handle: Any = None
        self.stderr_handle: Any = None

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def start(self) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.stdout_handle = (self.log_dir / "capture-api.stdout.log").open("w", encoding="utf-8")
        self.stderr_handle = (self.log_dir / "capture-api.stderr.log").open("w", encoding="utf-8")
        self.process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "approvaltrace.cli",
                "capture-api",
                "--host",
                "127.0.0.1",
                "--port",
                str(self.port),
                "--root",
                str(self.root),
            ],
            stdout=self.stdout_handle,
            stderr=self.stderr_handle,
            text=True,
        )
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError(f"Capture API exited with {self.process.returncode}")
            try:
                if _http_json(f"{self.base_url}/health") == {"status": "ok"}:
                    return
            except OSError:
                time.sleep(0.2)
        raise TimeoutError("Capture API did not become healthy")

    def stop(self) -> None:
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
        if self.stdout_handle is not None:
            self.stdout_handle.close()
        if self.stderr_handle is not None:
            self.stderr_handle.close()

    def __enter__(self) -> CaptureApiProcess:
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop()


class AutomatedClineBatch:
    def __init__(
        self,
        *,
        repo: Path,
        root: Path,
        editor_exe: Path,
        cline_extension: Path,
        scenarios: tuple[ScenarioProtocol, ...] = SCENARIOS,
    ) -> None:
        self.repo = repo.resolve()
        self.root = root.resolve()
        self.editor_exe = editor_exe.resolve()
        self.cline_extension = cline_extension.resolve()
        self.scenarios = scenarios

    def run(self) -> Path:
        batch_id = datetime.now().strftime("cline-%Y%m%d-%H%M%S")
        batch_dir = self.root / "batches" / batch_id
        batch_dir.mkdir(parents=True, exist_ok=False)
        extension_root = self.cline_extension.parent
        capture_port = _free_port()
        results: list[ScenarioResult] = []
        with CaptureApiProcess(
            root=batch_dir, port=capture_port, log_dir=batch_dir / "logs"
        ) as capture_api:
            for ordinal, protocol in enumerate(self.scenarios, start=1):
                result = self._run_scenario(
                    protocol=protocol,
                    ordinal=ordinal,
                    batch_dir=batch_dir,
                    extension_root=extension_root,
                    capture_base_url=capture_api.base_url,
                )
                results.append(result)
        summary = {
            "format": "approvaltrace-batch-v1",
            "generated_at": _now(),
            "client": f"Cline {self._cline_version()}",
            "results": [result.as_dict() for result in results],
        }
        write_json(batch_dir / "summary.json", summary)
        generate_batch_dashboard(batch_dir, summary)
        return batch_dir

    def _run_scenario(
        self,
        *,
        protocol: ScenarioProtocol,
        ordinal: int,
        batch_dir: Path,
        extension_root: Path,
        capture_base_url: str,
    ) -> ScenarioResult:
        run_id = f"cline-{protocol.scenario_id.lower().replace('-', '')}-{ordinal:03d}"
        run_dir = batch_dir / "runs" / run_id
        profile_dir = batch_dir / "runtime" / "profiles" / run_id
        workspace_dir = batch_dir / "runtime" / "workspaces" / run_id
        run_dir.mkdir(parents=True)
        scenario = load_scenario(protocol.scenario_id)
        scenario_file = next(
            (self.repo / "mutation_server" / "scenarios").glob(f"{protocol.scenario_id}-*.yaml")
        )
        initial_tool = tool_for_phase(scenario, "initial")
        mutated_tool = tool_for_phase(scenario, "mutated") if protocol.mutation else None
        mcp_config = self._mcp_config(batch_dir)
        seed_isolated_profile(user_data_dir=profile_dir, mcp_config=mcp_config)
        configuration_path = (
            profile_dir
            / "User"
            / "globalStorage"
            / "saoudrizwan.claude-dev"
            / "settings"
            / "cline_mcp_settings.json"
        )
        timeline: list[TimelineEvent] = []
        observation = UiObservation()
        captures: list[dict[str, Any]] = []
        error: str | None = None
        debug_port = _free_port()
        driver = ClinePlaywrightDriver(
            editor_exe=self.editor_exe,
            user_data_dir=profile_dir,
            extensions_dir=extension_root,
            extension_path=None,
            disabled_extension_ids=self._other_extension_ids(),
            workspace_dir=workspace_dir,
            debug_port=debug_port,
            log_dir=batch_dir / "logs" / run_id,
        )
        try:
            driver.start()
            driver.configure_provider(
                base_url=f"{capture_base_url}/v1",
                api_key="approvaltrace-local",
                model_id="approvaltrace-capture",
            )
            _http_json(
                f"{capture_base_url}/approvaltrace/activate",
                payload={
                    "run_id": run_id,
                    "scenario_id": protocol.scenario_id,
                    "phase": "initial",
                },
            )
            timeline.append(TimelineEvent(_now(), "activate", "initial"))
            driver.restart_mcp_server()
            timeline.append(TimelineEvent(_now(), "mcp_restart", "initial"))
            initial_ui = driver.snapshot(run_dir / "approval-before.png")
            observation.visible_text = initial_ui.visible_text
            observation.approval_shown = self._approval_dialog(initial_ui.dialogs)
            observation.visible_fields = self._visible_fields(initial_tool, initial_ui.visible_text)
            timeline.append(TimelineEvent(_now(), "ui_observed", "initial"))
            driver.start_new_task(protocol.prompt)
            driver.wait_for_completion()
            captures = _wait_for_capture(capture_base_url, run_id, 1)
            captures[0]["phase"] = "initial"
            timeline.append(TimelineEvent(_now(), "model_request", "initial", {"number": 1}))

            if protocol.mutation:
                _http_json(f"{capture_base_url}/approvaltrace/phase/mutated", payload={})
                timeline.append(TimelineEvent(_now(), "phase_change", "mutated"))
                if protocol.wait_after_mutation_seconds:
                    time.sleep(protocol.wait_after_mutation_seconds)
                notification_ui = driver.snapshot(run_dir / "notification.png")
                observation.notification_shown = (
                    "notifications/tools/list_changed" in notification_ui.visible_text
                )
                driver.open_mcp_servers()
                mutated_ui = driver.snapshot(run_dir / "approval-after.png")
                observation.warning_shown = bool(mutated_ui.alerts)
                observation.new_approval_shown = self._approval_dialog(mutated_ui.dialogs)
                observation.visible_diff_shown = "diff" in mutated_ui.visible_text.lower()
                observation.tool_list_refreshed = self._tool_visible(
                    mutated_tool or initial_tool, mutated_ui.visible_text
                )
                timeline.append(
                    TimelineEvent(
                        _now(),
                        "post_mutation_ui_observed",
                        "mutated",
                        {"automatic_refresh": observation.tool_list_refreshed},
                    )
                )
                driver.start_new_task(protocol.prompt)
                driver.wait_for_completion()
                captures = _wait_for_capture(capture_base_url, run_id, 2)
                for capture in captures:
                    capture["phase"] = "initial" if capture["request_number"] == 1 else "mutated"
                timeline.append(TimelineEvent(_now(), "model_request", "mutated", {"number": 2}))
                if protocol.marker and not self._capture_has_marker(captures[-1], protocol.marker):
                    if protocol.try_new_task_before_reconnect:
                        driver.start_new_task(protocol.prompt)
                        driver.wait_for_completion()
                        captures = _wait_for_capture(capture_base_url, run_id, 3)
                        for capture in captures:
                            capture["phase"] = (
                                "initial" if capture["request_number"] == 1 else "mutated"
                            )
                        timeline.append(TimelineEvent(_now(), "new_task_model_request", "mutated"))
                    if not self._capture_has_marker(captures[-1], protocol.marker):
                        observation.forced_reconnect = True
                        driver.restart_mcp_server()
                        reconnect_ui = driver.snapshot(run_dir / "approval-after-reconnect.png")
                        observation.new_approval_shown = (
                            observation.new_approval_shown
                            or self._approval_dialog(reconnect_ui.dialogs)
                        )
                        timeline.append(TimelineEvent(_now(), "forced_reconnect", "mutated"))
                        driver.start_new_task(protocol.prompt)
                        driver.wait_for_completion()
                        captures = _wait_for_capture(capture_base_url, run_id, len(captures) + 1)
                        for capture in captures:
                            capture["phase"] = (
                                "initial" if capture["request_number"] == 1 else "mutated"
                            )
                        timeline.append(TimelineEvent(_now(), "reconnect_model_request", "mutated"))
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            try:
                driver.write_diagnostics(run_dir)
            except Exception as diagnostic_exc:
                observation.notes.append(
                    f"diagnostic_capture_failed: {type(diagnostic_exc).__name__}: {diagnostic_exc}"
                )
            observation.notes.append(error)
            timeline.append(TimelineEvent(_now(), "automation_error", "unknown", {"error": error}))
        finally:
            driver.stop()

        changed_count = self._changed_requests(
            captures,
            marker=protocol.marker,
            reapproval=observation.new_approval_shown,
            mutation=protocol.mutation,
        )
        findings = self._classify(
            protocol=protocol,
            captures=captures,
            observation=observation,
            changed_count=changed_count,
            error=error,
        )
        environment = {
            "run_id": run_id,
            "scenario_id": protocol.scenario_id,
            "client_name": "Cline",
            "client_version": self._cline_version(),
            "operating_system": f"{platform.system()} {platform.release()} {platform.version()}",
            "python_version": platform.python_version(),
            "approvaltrace_commit": _git_sha(self.repo),
            "configuration_hash": _sha256(configuration_path),
            "capture_api": capture_base_url,
            "mcp_transport": "stdio",
            "profile_state": "fresh_isolated",
            "started_at": timeline[0].timestamp if timeline else _now(),
            "automation": "playwright_cdp",
        }
        model_extraction, evidence_complete = build_run_evidence(
            run_dir=run_dir,
            scenario_file=scenario_file,
            initial_tool=initial_tool,
            mutated_tool=mutated_tool,
            captures=captures,
            ui_observation=observation.as_dict(),
            environment=environment,
            timeline=[event.__dict__ for event in timeline],
            findings=findings,
        )
        shutil.rmtree(profile_dir, ignore_errors=True)
        shutil.rmtree(workspace_dir, ignore_errors=True)
        return ScenarioResult(
            run_id=run_id,
            scenario_id=protocol.scenario_id,
            title=scenario["title"],
            result=findings["result"],
            severity=findings["severity"],
            reasons=findings["reasons"],
            capture_count=len(captures),
            changed_requests_before_reapproval=changed_count,
            model_extraction=model_extraction,
            evidence_complete=evidence_complete,
            notification_expected=protocol.notification_expected,
            notification_observed=observation.notification_shown,
            automatic_refresh=observation.tool_list_refreshed,
            reapproval_observed=observation.new_approval_shown,
        )

    def _mcp_config(self, batch_dir: Path) -> dict[str, Any]:
        return {
            "mcpServers": {
                "approvaltrace": {
                    "autoApprove": [],
                    "disabled": False,
                    "timeout": 60,
                    "type": "stdio",
                    "command": sys.executable,
                    "args": ["-m", "mutation_server.server"],
                    "env": {
                        "PYTHONPATH": str(self.repo),
                        "APPROVALTRACE_STATE_FILE": str(batch_dir / "server-state.json"),
                        "APPROVALTRACE_SCENARIO_DIR": str(
                            self.repo / "mutation_server" / "scenarios"
                        ),
                    },
                }
            }
        }

    def _cline_version(self) -> str:
        package = json.loads((self.cline_extension / "package.json").read_text(encoding="utf-8"))
        return str(package["version"])

    def _other_extension_ids(self) -> tuple[str, ...]:
        registry = self.cline_extension.parent / "extensions.json"
        if not registry.exists():
            return ()
        package = json.loads((self.cline_extension / "package.json").read_text(encoding="utf-8"))
        cline_id = f"{package['publisher']}.{package['name']}"
        records = json.loads(registry.read_text(encoding="utf-8"))
        return tuple(
            sorted(
                {
                    str(record.get("identifier", {}).get("id", ""))
                    for record in records
                    if record.get("identifier", {}).get("id")
                    and record.get("identifier", {}).get("id") != cline_id
                }
            )
        )

    @staticmethod
    def _approval_dialog(dialogs: tuple[str, ...]) -> bool:
        return any(
            any(term in text.lower() for term in ("approve", "approval", "allow", "trust"))
            for text in dialogs
        )

    @staticmethod
    def _tool_visible(tool: dict[str, Any], text: str) -> bool:
        properties = tool.get("inputSchema", {}).get("properties", {})
        return tool.get("name", "") in text and all(name in text for name in properties)

    @classmethod
    def _visible_fields(cls, tool: dict[str, Any], text: str) -> dict[str, str]:
        properties = tool.get("inputSchema", {}).get("properties", {})
        visible_property_names = sum(name in text for name in properties)
        full_schema = visible_property_names == len(properties) and all(
            str(value.get("type", "")) in text and str(value.get("description", "")) in text
            for value in properties.values()
        )
        schema_visibility = (
            "full" if full_schema else "partial" if visible_property_names else "absent"
        )
        return {
            "tool_name": "full" if tool.get("name", "") in text else "absent",
            "tool_description": ("full" if str(tool.get("description", "")) in text else "absent"),
            "input_schema": schema_visibility,
            "output_schema": "not_applicable" if "outputSchema" not in tool else "absent",
            "annotations": "full" if "readOnlyHint" in text else "absent",
            "execution": "not_applicable" if "execution" not in tool else "absent",
            "meta": "not_applicable" if "_meta" not in tool else "absent",
        }

    @staticmethod
    def _capture_has_marker(capture: dict[str, Any], marker: str) -> bool:
        tool, _ = extract_model_tool(
            capture.get("body", {}),
            server_name="approvaltrace",
            tool_name="search_test_documents",
        )
        if tool is None:
            return False
        encoded = json.dumps(tool, ensure_ascii=False)
        return marker in encoded or marker in decode_tag_text(encoded)

    @classmethod
    def _changed_requests(
        cls,
        captures: list[dict[str, Any]],
        *,
        marker: str | None,
        reapproval: bool | None,
        mutation: bool,
    ) -> int:
        if not mutation or not marker or reapproval:
            return 0
        return sum(
            capture.get("phase") == "mutated" and cls._capture_has_marker(capture, marker)
            for capture in captures
        )

    @classmethod
    def _classify(
        cls,
        *,
        protocol: ScenarioProtocol,
        captures: list[dict[str, Any]],
        observation: UiObservation,
        changed_count: int,
        error: str | None,
    ) -> dict[str, Any]:
        if error or not captures:
            return {
                "result": "INCONCLUSIVE",
                "severity": "info",
                "reasons": ["automation_or_capture_incomplete"],
                "error": error,
                "changed_requests_before_reapproval": changed_count,
            }
        hidden = False
        if protocol.scenario_id == "AT-002":
            marker_in_model = any(
                cls._capture_has_marker(capture, protocol.marker or "") for capture in captures
            )
            marker_visibly_named = bool(
                protocol.marker and protocol.marker in observation.visible_text
            )
            hidden = marker_in_model and not marker_visibly_named
        schema_visibility = observation.visible_fields.get("input_schema")
        finding = classify_run(
            hidden_model_content=hidden,
            material_mutation=protocol.mutation,
            reapproval_observed=(observation.new_approval_shown if protocol.mutation else False),
            changed_requests_before_reapproval=changed_count,
            schema_visibility=schema_visibility,
        )
        if protocol.scenario_id == "AT-006" and changed_count == 0:
            finding["reasons"].append("silent_mutation_behavior_reported_separately")
        finding["changed_requests_before_reapproval"] = changed_count
        return finding
