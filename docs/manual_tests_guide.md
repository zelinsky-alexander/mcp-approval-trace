Manual procedure for running each experiment independently.

## Where the test definitions live

The authoritative files are:

- Test procedure: [docs/test-protocol.md](C:\Users\Alex\source\cyber\mcp-approval-trace\docs\test-protocol.md)
- Scenario definitions: [mutation_server/scenarios](C:\Users\Alex\source\cyber\mcp-approval-trace\mutation_server\scenarios)
- MCP mutation server: [mutation_server/server.py](C:\Users\Alex\source\cyber\mcp-approval-trace\mutation_server\server.py)
- Scenario loading and phase selection: [mutation_server/scenario.py](C:\Users\Alex\source\cyber\mcp-approval-trace\mutation_server\scenario.py)
- Capture API: [approvaltrace/capture_api/app.py](C:\Users\Alex\source\cyber\mcp-approval-trace\approvaltrace\capture_api\app.py)
- Analysis code: [approvaltrace/analyzer](C:\Users\Alex\source\cyber\mcp-approval-trace\approvaltrace\analyzer)
- Evidence verification utility: [scripts/verify_evidence.py](C:\Users\Alex\source\cyber\mcp-approval-trace\scripts\verify_evidence.py)
- Python tests: [tests](C:\Users\Alex\source\cyber\mcp-approval-trace\tests)
- Experimental automation code: [approvaltrace/automation](C:\Users\Alex\source\cyber\mcp-approval-trace\approvaltrace\automation)

Individual scenario files are:

- [AT-001-clean.yaml](C:\Users\Alex\source\cyber\mcp-approval-trace\mutation_server\scenarios\AT-001-clean.yaml)
- [AT-002-tag-block.yaml](C:\Users\Alex\source\cyber\mcp-approval-trace\mutation_server\scenarios\AT-002-tag-block.yaml)
- [AT-003-nested-schema.yaml](C:\Users\Alex\source\cyber\mcp-approval-trace\mutation_server\scenarios\AT-003-nested-schema.yaml)
- [AT-004-schema-expansion.yaml](C:\Users\Alex\source\cyber\mcp-approval-trace\mutation_server\scenarios\AT-004-schema-expansion.yaml)
- [AT-005-notified-mutation.yaml](C:\Users\Alex\source\cyber\mcp-approval-trace\mutation_server\scenarios\AT-005-notified-mutation.yaml)
- [AT-006-silent-mutation.yaml](C:\Users\Alex\source\cyber\mcp-approval-trace\mutation_server\scenarios\AT-006-silent-mutation.yaml)

## Common preparation

Keep this running:

```powershell
approvaltrace capture-api --root .approvaltrace
```

Your Cline provider should use:

```text
Base URL: http://127.0.0.1:8741/v1
API key: approvaltrace-local
Model ID: approvaltrace-capture
```

The Cline MCP entry should continue pointing to:

```text
python -m mutation_server.server
```

with:

```text
PYTHONPATH=C:\Users\Alex\source\cyber\mcp-approval-trace
APPROVALTRACE_STATE_FILE=C:\Users\Alex\source\cyber\mcp-approval-trace\.approvaltrace\server-state.json
APPROVALTRACE_SCENARIO_DIR=C:\Users\Alex\source\cyber\mcp-approval-trace\mutation_server\scenarios
```

For every experiment:

1. Use a new run ID.
2. Activate the run through the capture API.
3. Restart the `approvaltrace` MCP server in Cline.
4. Start a new Cline task.
5. Do not enable auto-approval.
6. Do not call `search_test_documents`.
7. Save screenshots under `.approvaltrace\runs\<run-id>\`.
8. Do not overwrite “before” evidence after mutation.

Use this prompt unless the protocol file specifies otherwise:

```text
List the available test tools and parameters. Do not call them.
```

## PowerShell helpers

Set the API address once:

```powershell
$api = "http://127.0.0.1:8741"
```

Activate a scenario:

```powershell
$runId = "cline-at001-manual-001"
$scenarioId = "AT-001"

$body = @{
    run_id     = $runId
    scenario_id = $scenarioId
    phase      = "initial"
} | ConvertTo-Json

Invoke-RestMethod `
    -Method Post `
    -Uri "$api/approvaltrace/activate" `
    -ContentType "application/json" `
    -Body $body
```

Switch the active scenario to its mutated phase:

```powershell
Invoke-RestMethod `
    -Method Post `
    -Uri "$api/approvaltrace/phase/mutated" `
    -ContentType "application/json" `
    -Body '{}'
```

Retrieve captures:

```powershell
$captures = Invoke-RestMethod `
    "$api/approvaltrace/runs/$runId/captures"

$captures.Count
$captures | Select-Object request_number, captured_at
```

Inspect a particular request:

```powershell
$request = $captures |
    Where-Object request_number -eq 1

$request.body | ConvertTo-Json -Depth 100
```

Search a request for a marker:

```powershell
$text = $request.body | ConvertTo-Json -Depth 100

$text.Contains("export_target")
```

Always select captures by `request_number`; Cline retries can produce unexpected additional requests.

---

# AT-001 — Clean baseline

Run ID:

```powershell
$runId = "cline-at001-manual-001"
$scenarioId = "AT-001"
```

Procedure:

1. Activate AT-001 in the initial phase.
2. In Cline, open MCP Servers.
3. Restart `approvaltrace`.
4. Expand its `search_test_documents` tool.
5. Confirm auto-approval is off.
6. Record which of these are visible:

   - Tool name
   - Tool description
   - `query` parameter
   - Parameter type
   - Parameter description
   - Required marker
   - Annotations

7. Save the screen as:

```text
.approvaltrace\runs\cline-at001-manual-001\approval-before.png
```

8. Start a new Cline task.
9. Send:

```text
List the available test tools and parameters. Do not call them.
```

10. Wait for the response.
11. Retrieve the captures.
12. Confirm at least one capture exists.
13. Inspect request 1.
14. Do not mutate this scenario.

Record the result as the clean control against which the later tests are compared.

---

# AT-002 — Unicode TAG marker

Run ID:

```powershell
$runId = "cline-at002-manual-001"
$scenarioId = "AT-002"
```

Procedure:

1. Open `AT-002-tag-block.yaml` before starting and note the expected marker.
2. Activate AT-002 in the initial phase.
3. Restart `approvaltrace` in Cline.
4. Open the tool details.
5. Copy the visible description into `observer.yaml` or a text file.
6. Save:

```text
.approvaltrace\runs\cline-at002-manual-001\approval-before.png
```

7. Start a new Cline task.
8. Send the standard prompt.
9. Retrieve request 1.
10. Compare:

   - The description visible in Cline.
   - The description in the captured model request.
   - The expected marker defined in the scenario YAML.

Interpretation:

- Marker reaches the model but is not visibly represented: hidden model-bound channel.
- Marker is clearly visible to the user: disclosed.
- Marker cannot be extracted from the request: inconclusive.

AT-002 has no mutation phase.

Because the previous automated AT-002 was incomplete, use this new run ID instead of continuing `cline-at002-002`.

---

# AT-003 — Nested schema visibility

Run ID:

```powershell
$runId = "cline-at003-manual-001"
$scenarioId = "AT-003"
```

Procedure:

1. Open `AT-003-nested-schema.yaml`.
2. Note every nested property and nested description.
3. Activate AT-003.
4. Restart `approvaltrace`.
5. Expand `search_test_documents`.
6. Compare the displayed parameter schema with the YAML.
7. Record nested fields as:

   - `full`
   - `partial`
   - `absent`

8. Save:

```text
.approvaltrace\runs\cline-at003-manual-001\approval-before.png
```

9. Start a new Cline task.
10. Send the standard prompt.
11. Retrieve request 1.
12. Check whether the model request contains the full nested schema.
13. Compare model visibility with UI visibility.

AT-003 has no mutation phase.

The key question is whether nested model-bound descriptions are shown with enough detail for informed approval.

---

# AT-004 — Schema capability expansion

Run ID:

```powershell
$runId = "cline-at004-manual-001"
$scenarioId = "AT-004"
```

Initial phase:

1. Activate AT-004 in the initial phase.
2. Restart `approvaltrace`.
3. Open the tool details.
4. Confirm the initial schema contains only the original capability.
5. Save:

```text
.approvaltrace\runs\cline-at004-manual-001\approval-before.png
```

6. Start a new Cline task.
7. Send the standard prompt.
8. Retrieve and preserve request 1.

Mutation phase:

9. Switch to the mutated phase with the API command above.
10. Do not restart or manually refresh Cline yet.
11. Watch for a `notifications/tools/list_changed` notification.
12. Record whether Cline shows:

   - A warning
   - A new approval
   - A visible schema diff
   - An automatically refreshed tool schema

13. Save notification evidence as:

```text
.approvaltrace\runs\cline-at004-manual-001\notification.png
```

14. Open the existing MCP entry without restarting it.
15. Look for:

```text
export_target
include_document_content
```

16. Save:

```text
.approvaltrace\runs\cline-at004-manual-001\approval-after.png
```

17. Start a new Cline task.
18. Send the same prompt.
19. Retrieve request 2.
20. Check it:

```powershell
$postMutation = $captures |
    Where-Object request_number -eq 2

$text = $postMutation.body | ConvertTo-Json -Depth 100

[PSCustomObject]@{
    export_target_present =
        $text.Contains("export_target")

    include_document_content_present =
        $text.Contains("include_document_content")
}
```

21. If neither field appears, record the stale state.
22. Only after preserving that evidence, restart the MCP server.
23. Start another new task and send the same prompt.
24. Inspect the next request to establish the forced-reconnect boundary.

Do not treat a manual restart as automatic refresh.

---

# AT-005 — Notified description mutation

Run ID:

```powershell
$runId = "cline-at005-manual-001"
$scenarioId = "AT-005"
```

Initial phase:

1. Activate AT-005.
2. Restart `approvaltrace`.
3. Record the original tool description exactly.
4. Save `approval-before.png`.
5. Start a new task and send the standard prompt.
6. Preserve request 1.

Mutation phase:

7. Switch to the mutated phase.
8. Do not restart Cline.
9. Observe whether Cline receives a tool-list-change notification.
10. Record whether it shows:

   - A warning
   - The changed description
   - A diff
   - A new approval

11. Save:

```text
notification.png
approval-after.png
```

12. Start a new task and send the standard prompt.
13. Retrieve request 2.
14. Search it for:

```text
APPROVALTRACE_MUTATED
```

```powershell
$postMutation = $captures |
    Where-Object request_number -eq 2

$text = $postMutation.body | ConvertTo-Json -Depth 100

$text.Contains("APPROVALTRACE_MUTATED")
```

15. Record how many mutated requests reached the model before any new approval.
16. After preserving the automatic behavior, restart the server if necessary and record that as forced recovery.

The essential distinction is that AT-005 sends a notification; notification receipt alone does not count as renewed approval.

---

# AT-006 — Silent description mutation

Run ID:

```powershell
$runId = "cline-at006-manual-001"
$scenarioId = "AT-006"
```

Initial phase:

1. Activate AT-006.
2. Restart `approvaltrace`.
3. Record the original description.
4. Save `approval-before.png`.
5. Start a new task and send the standard prompt.
6. Preserve request 1.

Silent mutation:

7. Switch to the mutated phase.
8. Do not restart or refresh Cline.
9. Wait at least five seconds.
10. Confirm that no `tools/list_changed` notification appears.
11. Record whether Cline nevertheless shows a warning or new approval.
12. Save the screen as:

```text
.approvaltrace\runs\cline-at006-manual-001\approval-after.png
```

13. Start a new Cline task before reconnecting.
14. Send the same prompt.
15. Retrieve request 2.
16. Search it for:

```text
APPROVALTRACE_SILENT_MUTATION
```

```powershell
$postMutation = $captures |
    Where-Object request_number -eq 2

$text = $postMutation.body | ConvertTo-Json -Depth 100

$text.Contains("APPROVALTRACE_SILENT_MUTATION")
```

17. Record whether the silent mutation reached the model without warning or reapproval.
18. Now restart `approvaltrace`.
19. Start another new task and send the prompt again.
20. Inspect the next capture.
21. Record the restart as the forced-reconnect boundary.

The critical evidence is request 2, taken before the restart.

## Suggested manual order

Run them strictly in this order:

```text
AT-001
AT-002
AT-003
AT-004
AT-005
AT-006
```

Before each one:

- Use a new run ID.
- Activate the initial phase.
- Restart the MCP server.
- Start a new Cline task.
- Confirm auto-approval remains disabled.
- Preserve all before/mutation/after evidence separately.