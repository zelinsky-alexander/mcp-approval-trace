# Automated Cline experiments

The automated runner launches a disposable Visual Studio Code profile containing only the
installed Cline extension. It drives Cline's real webview through a loopback-only Chrome
DevTools Protocol connection, captures visible UI evidence, and sends model-bound requests to
a dedicated ApprovalTrace capture API.

```powershell
approvaltrace automate cline
```

Run selected scenarios:

```powershell
approvaltrace automate cline --scenario AT-001 --scenario AT-004
```

The runner does not copy the normal VS Code user profile, credentials, task history, or
workspace. Every scenario receives a fresh user-data directory and an empty synthetic
workspace. Auto-approval is disabled. Runtime profiles are removed after evidence generation.

Batch output is stored under:

```text
.approvaltrace/batches/<batch-id>/
```

The batch `report.html` summarizes all scenario outcomes and links to per-run reports.

## Evidence boundary

UI classifications are derived only from visible DOM text, semantic dialogs/alerts, and saved
screenshots. If Cline's UI cannot be located or its model-bound MCP block cannot be parsed
deterministically, the scenario is `INCONCLUSIVE`. The runner never treats server metadata as
proof that the same metadata was visible in Cline.

## Dependency

UI automation is an optional extra:

```powershell
python -m pip install -e ".[automation]"
```

`playwright` is used only as a CDP client for Visual Studio Code's existing Electron runtime;
the runner does not download or launch a separate browser.
