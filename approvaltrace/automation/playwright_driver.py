from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, Frame, Page, Playwright, sync_playwright


@dataclass(frozen=True)
class UiSnapshot:
    visible_text: str
    dialogs: tuple[str, ...]
    alerts: tuple[str, ...]


def seed_isolated_profile(
    *,
    user_data_dir: Path,
    mcp_config: dict[str, Any],
) -> None:
    user_dir = user_data_dir / "User"
    user_dir.mkdir(parents=True, exist_ok=True)
    (user_dir / "settings.json").write_text(
        json.dumps(
            {
                "workbench.startupEditor": "none",
                "security.workspace.trust.enabled": False,
                "telemetry.telemetryLevel": "off",
                "update.mode": "none",
                "extensions.autoUpdate": False,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (user_dir / "keybindings.json").write_text(
        json.dumps(
            [
                {
                    "key": "ctrl+alt+shift+s",
                    "command": "cline.settingsButtonClicked",
                },
                {
                    "key": "ctrl+alt+shift+m",
                    "command": "cline.mcpButtonClicked",
                },
                {
                    "key": "ctrl+alt+shift+n",
                    "command": "cline.plusButtonClicked",
                },
            ],
            indent=2,
        ),
        encoding="utf-8",
    )
    mcp_path = (
        user_dir
        / "globalStorage"
        / "saoudrizwan.claude-dev"
        / "settings"
        / "cline_mcp_settings.json"
    )
    mcp_path.parent.mkdir(parents=True, exist_ok=True)
    mcp_path.write_text(json.dumps(mcp_config, indent=2), encoding="utf-8")


def copy_cline_extension(source: Path, extension_root: Path) -> Path:
    destination = extension_root / source.name
    if not destination.exists():
        extension_root.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, destination)
    package = json.loads((destination / "package.json").read_text(encoding="utf-8"))
    identifier = f"{package['publisher']}.{package['name']}"
    installed_record: dict[str, Any] = {}
    installed_registry = source.parent / "extensions.json"
    if installed_registry.exists():
        records = json.loads(installed_registry.read_text(encoding="utf-8"))
        installed_record = next(
            (
                record
                for record in records
                if record.get("identifier", {}).get("id") == identifier
                and record.get("version") == package["version"]
            ),
            {},
        )
    resolved = destination.resolve().as_posix()
    if len(resolved) > 1 and resolved[1] == ":":
        resolved = resolved[0].lower() + resolved[1:]
    location = "/" + resolved.lstrip("/")
    registration = {
        **installed_record,
        "identifier": installed_record.get("identifier", {"id": identifier}),
        "version": package["version"],
        "location": {
            "$mid": 1,
            "path": location,
            "scheme": "file",
        },
        "relativeLocation": destination.name,
    }
    (extension_root / "extensions.json").write_text(
        json.dumps(
            [registration],
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    return destination


class ClinePlaywrightDriver:
    def __init__(
        self,
        *,
        editor_exe: Path,
        user_data_dir: Path,
        extensions_dir: Path,
        extension_path: Path | None,
        workspace_dir: Path,
        debug_port: int,
        log_dir: Path,
        disabled_extension_ids: tuple[str, ...] = (),
        timeout_seconds: float = 45.0,
    ) -> None:
        self.editor_exe = editor_exe
        self.user_data_dir = user_data_dir
        self.extensions_dir = extensions_dir
        self.extension_path = extension_path
        self.disabled_extension_ids = disabled_extension_ids
        self.workspace_dir = workspace_dir
        self.debug_port = debug_port
        self.log_dir = log_dir
        self.timeout_ms = int(timeout_seconds * 1000)
        self.process: subprocess.Popen[bytes] | None = None
        self.playwright: Playwright | None = None
        self.browser: Browser | None = None
        self.workbench: Page | None = None
        self.stdout_handle: Any = None
        self.stderr_handle: Any = None

    def start(self) -> None:
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.stdout_handle = (self.log_dir / "vscode.stdout.log").open("wb")
        self.stderr_handle = (self.log_dir / "vscode.stderr.log").open("wb")
        creation_flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        child_environment = os.environ.copy()
        child_environment.pop("ELECTRON_RUN_AS_NODE", None)
        arguments = [
            str(self.editor_exe),
            "--new-window",
            "--skip-welcome",
            "--disable-workspace-trust",
            "--disable-updates",
            "--disable-crash-reporter",
            "--no-sandbox",
            "--user-data-dir",
            str(self.user_data_dir),
            "--extensions-dir",
            str(self.extensions_dir),
        ]
        if self.extension_path is not None:
            arguments.append(f"--extensionDevelopmentPath={self.extension_path}")
        arguments.extend(
            f"--disable-extension={identifier}" for identifier in self.disabled_extension_ids
        )
        arguments.extend(
            [
                "--remote-debugging-address=127.0.0.1",
                f"--remote-debugging-port={self.debug_port}",
                str(self.workspace_dir),
            ]
        )
        self.process = subprocess.Popen(
            arguments,
            cwd=self.workspace_dir,
            creationflags=creation_flags,
            env=child_environment,
            stdout=self.stdout_handle,
            stderr=self.stderr_handle,
        )
        deadline = time.monotonic() + self.timeout_ms / 1000
        endpoint = f"http://127.0.0.1:{self.debug_port}/json/version"
        launcher_exit: int | None = None
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(endpoint, timeout=1):
                    break
            except OSError:
                launcher_exit = self.process.poll()
                time.sleep(0.25)
        else:
            self._flush_logs()
            diagnostic = self._read_stderr_tail()
            suffix = "" if launcher_exit is None else f"; launcher exit code {launcher_exit}"
            if diagnostic:
                suffix += f"; stderr: {diagnostic}"
            raise TimeoutError(f"VS Code debugging endpoint did not become ready{suffix}")
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.connect_over_cdp(
            f"http://127.0.0.1:{self.debug_port}"
        )
        pages = [page for context in self.browser.contexts for page in context.pages]
        if not pages:
            raise RuntimeError("VS Code exposed no CDP page")
        self.workbench = max(pages, key=lambda page: len(page.frames))
        self.workbench.wait_for_timeout(8000)

    def stop(self) -> None:
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
        if self.browser is not None:
            try:
                self.browser.close()
            except Exception:
                pass
        if self.playwright is not None:
            try:
                self.playwright.stop()
            except Exception:
                pass
        self._close_logs()
        self.browser = None
        self.playwright = None
        self.process = None

    def _flush_logs(self) -> None:
        for handle in (self.stdout_handle, self.stderr_handle):
            if handle is not None:
                handle.flush()

    def _close_logs(self) -> None:
        for handle in (self.stdout_handle, self.stderr_handle):
            if handle is not None:
                handle.close()
        self.stdout_handle = None
        self.stderr_handle = None

    def _read_stderr_tail(self) -> str:
        path = self.log_dir / "vscode.stderr.log"
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8", errors="replace")[-1000:].strip()

    def __enter__(self) -> ClinePlaywrightDriver:
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop()

    def _require_workbench(self) -> Page:
        if self.workbench is None:
            raise RuntimeError("Driver is not started")
        return self.workbench

    def _command(self, label: str) -> None:
        page = self._require_workbench()
        cline_actions = {
            "Cline: Settings": ("Settings", "settings-gear"),
            "Cline: MCP Servers": ("MCP Servers", "server"),
            "Cline: New Task": ("New Task", "add"),
        }
        if label in cline_actions:
            accessible_name, codicon = cline_actions[label]
            icon = page.locator(f"[aria-label='{accessible_name}']").first
            if icon.count() == 0:
                icon = page.locator(f".part.sidebar .codicon-{codicon}").first
            icon.wait_for(state="attached", timeout=self.timeout_ms)
            action = icon if icon.is_visible() else icon.locator("xpath=..")
            action.click()
            page.wait_for_timeout(1500)
            return
        page.keyboard.press("Control+Shift+P")
        palette = page.locator("input[aria-label*='command' i]").last
        palette.wait_for(state="visible", timeout=self.timeout_ms)
        title = label.rsplit(":", 1)[-1].strip()
        palette.fill(f">{title}")
        rows = page.locator(".quick-input-widget .monaco-list-row")
        rows.first.wait_for(state="visible", timeout=self.timeout_ms)
        row_texts = rows.all_inner_texts()
        preferred = next(
            (
                index
                for index, text in enumerate(row_texts)
                if title.lower() in text.lower() and "cline" in text.lower()
            ),
            None,
        )
        if preferred is None:
            preferred = next(
                (index for index, text in enumerate(row_texts) if title.lower() in text.lower()),
                None,
            )
        if preferred is None:
            raise RuntimeError(
                f"Command {label!r} was not found; visible choices: {row_texts[:10]}"
            )
        rows.nth(preferred).click()
        page.wait_for_timeout(1200)

    def open_cline(self) -> None:
        page = self._require_workbench()
        activity = page.locator(".activitybar [aria-label*='Cline' i]")
        if activity.count() == 0:
            activity = page.locator("[id='workbench.view.extension.claude-dev-ActivityBar']")
        activity.first.wait_for(state="visible", timeout=self.timeout_ms)
        activity.first.click()
        page.wait_for_timeout(2000)
        self._cline_surface()

    def write_diagnostics(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        if self.workbench is not None:
            self.workbench.screenshot(
                path=directory / "automation-error-workbench.png", full_page=True
            )
        surface_texts: list[dict[str, Any]] = []
        for index, surface in enumerate(self._surfaces()):
            try:
                surface_texts.append(
                    {
                        "index": index,
                        "url": getattr(surface, "url", ""),
                        "text": surface.locator("body").inner_text(timeout=1000),
                    }
                )
            except Exception as exc:
                surface_texts.append(
                    {
                        "index": index,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
        (directory / "automation-error-surfaces.json").write_text(
            json.dumps(surface_texts, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _surfaces(self) -> list[Page | Frame]:
        if self.browser is None:
            return []
        surfaces: list[Page | Frame] = []
        for context in self.browser.contexts:
            for page in context.pages:
                surfaces.append(page)
                surfaces.extend(page.frames)
        return surfaces

    def _cline_surface(self) -> Page | Frame:
        candidates: list[tuple[int, Page | Frame]] = []
        for surface in self._surfaces():
            try:
                text = surface.locator("body").inner_text(timeout=1500)
            except Exception:
                continue
            marker_score = sum(
                marker.lower() in text.lower()
                for marker in ("Cline", "MCP Servers", "API Provider", "Auto-approve")
            )
            url = getattr(surface, "url", "")
            score = marker_score * 10 + (100 if url.startswith("vscode-webview://") else 0)
            if marker_score:
                candidates.append((score, surface))
        if not candidates:
            raise RuntimeError("Could not locate the Cline webview")
        return max(candidates, key=lambda item: item[0])[1]

    def configure_provider(self, *, base_url: str, api_key: str, model_id: str) -> None:
        self.open_cline()
        self._command("Cline: Settings")
        surface = self._cline_surface()
        surface.get_by_text("API Provider", exact=False).first.wait_for(
            state="visible", timeout=self.timeout_ms
        )
        provider_select = surface.locator("select").filter(has=surface.locator("option"))
        selected = False
        for index in range(provider_select.count()):
            select = provider_select.nth(index)
            options = select.locator("option").all_text_contents()
            match = next((item for item in options if "OpenAI Compatible" in item), None)
            if match:
                select.select_option(label=match)
                selected = True
                break
        if not selected:
            provider_input = surface.locator("#api-provider input")
            if provider_input.count() == 0:
                provider_input = surface.locator("input[placeholder*='provider' i]")
            provider_input.first.click()
            provider_input.first.fill("OpenAI Compatible")
            option = surface.get_by_text("OpenAI Compatible", exact=True)
            option.last.wait_for(state="visible", timeout=self.timeout_ms)
            option.last.click()
            surface.wait_for_timeout(750)
        self._fill_labeled(surface, ("Base URL", "OpenAI Base URL"), base_url)
        self._fill_labeled(
            surface,
            ("OpenAI Compatible API Key", "OpenAI API Key", "API Key"),
            api_key,
        )
        self._fill_labeled(surface, ("Model ID", "Model"), model_id)
        save = surface.get_by_role("button", name="Save", exact=False)
        if save.count():
            save.last.click()
        surface.wait_for_timeout(500)

    def _fill_labeled(self, surface: Page | Frame, labels: tuple[str, ...], value: str) -> None:
        for label in labels:
            locator = surface.get_by_label(label, exact=False)
            if locator.count():
                locator.last.fill(value)
                return
        for label in labels:
            text = surface.get_by_text(label, exact=True)
            if text.count() == 0:
                text = surface.get_by_text(label, exact=False)
            if text.count():
                container = text.last
                for _ in range(4):
                    container = container.locator("xpath=..")
                    field = container.locator("input:visible, textarea:visible")
                    if field.count():
                        field.first.fill(value)
                        return
        raise RuntimeError(f"Could not find a field labelled one of {labels}")

    def open_mcp_servers(self) -> None:
        self._command("Cline: MCP Servers")
        surface = self._cline_surface()
        configure = surface.get_by_text("Configure", exact=True)
        if configure.count():
            configure.last.click()
        surface.get_by_text("approvaltrace", exact=True).first.wait_for(
            state="visible", timeout=self.timeout_ms
        )

    def restart_mcp_server(self) -> None:
        self.open_mcp_servers()
        surface = self._cline_surface()
        surface.get_by_role("button", name="Restart Server", exact=True).click()
        surface.wait_for_timeout(1500)

    def start_new_task(self, prompt: str) -> None:
        self._command("Cline: New Task")
        surface = self._cline_surface()
        inputs = surface.locator("textarea:visible")
        if inputs.count() == 0:
            inputs = surface.locator("[contenteditable='true']:visible")
        inputs.first.wait_for(state="visible", timeout=self.timeout_ms)
        inputs.first.fill(prompt)
        inputs.first.press("Enter")

    def wait_for_completion(self) -> None:
        surface = self._cline_surface()
        surface.get_by_text("ApprovalTrace capture complete.", exact=False).last.wait_for(
            state="visible", timeout=self.timeout_ms
        )

    def snapshot(self, path: Path) -> UiSnapshot:
        surface = self._cline_surface()
        visible_text = surface.locator("body").inner_text(timeout=self.timeout_ms)
        dialogs = tuple(surface.locator("[role='dialog']").all_inner_texts())
        alerts = tuple(surface.locator("[role='alert']").all_inner_texts())
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(surface, Page):
            surface.screenshot(path=path, full_page=True)
        else:
            surface.locator("body").screenshot(path=path)
        return UiSnapshot(visible_text=visible_text, dialogs=dialogs, alerts=alerts)
