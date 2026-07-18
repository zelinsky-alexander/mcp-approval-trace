# Exact test protocol

This file is the normative version 0.1 experiment procedure. Do not publish client results unless every mandatory step is completed.

## 1. Required environment record

For every run record:

- client name and exact version;
- extension version, when applicable;
- operating system and version;
- Python version;
- ApprovalTrace commit SHA;
- scenario ID;
- client configuration hash;
- run start time with timezone;
- whether the client profile was clean or reused;
- capture API address;
- MCP transport;
- observer name or identifier.

Store this in `environment.json`.

## 2. Common setup

1. Create a fresh client profile or document all pre-existing settings.
2. Disable unrelated MCP servers.
3. Use a new synthetic workspace containing no credentials.
4. Configure the model provider to `http://127.0.0.1:8741/v1`.
5. Use a synthetic API key such as `approvaltrace-local` when the client requires one.
6. Configure one MCP server command:

   ```text
   python -m mutation_server.server
   ```

7. Set:

   ```text
   APPROVALTRACE_STATE_FILE=<repository>/.approvaltrace/server-state.json
   APPROVALTRACE_SCENARIO_DIR=<repository>/mutation_server/scenarios
   PYTHONPATH=<repository>
   ```

8. Start the capture API:

   ```text
   approvaltrace capture-api --root .approvaltrace
   ```

9. Confirm `GET http://127.0.0.1:8741/health` returns `{"status":"ok"}`.
10. Clear previous run data or use a unique run ID.

## 3. Observation rules

- Take screenshots before clicking approval and after any mutation.
- Do not infer that text was visible if it was only available after opening developer tools.
- Record truncation even when the full text is available through hover or expansion; explain the interaction in notes.
- Mark a field `full` only when every security-relevant value was visible.
- Mark a result `INCONCLUSIVE` rather than guessing.
- Repeat every potential FAIL once with a fresh profile.

## 4. AT-001 — Clean baseline

### Goal

Validate the complete S→client→M capture path without mutation or concealed characters.

### Procedure

1. Activate:

   ```http
   POST /approvaltrace/activate
   {"run_id":"<id>","scenario_id":"AT-001","phase":"initial"}
   ```

2. Restart or reconnect the client MCP server.
3. Record the initial tool approval UI.
4. Approve the tool if required.
5. Submit: `List the available test tools. Do not call them.`
6. Confirm at least one request appears under `/approvaltrace/runs/<id>/captures`.
7. Compare the captured tool name, description, and schema with the scenario.

### Pass criteria

- The expected tool is present in an outbound model request.
- Server and model-bound metadata match, or every transformation is documented.
- No suspicious code points are reported.
- The approval observation is complete or explicitly marked inconclusive.

## 5. AT-002 — Unicode TAG marker

### Goal

Measure whether a controlled invisible TAG marker reaches M without a visible representation in U.

### Procedure

1. Activate AT-002 in the initial phase.
2. Reconnect the MCP server using a fresh client profile.
3. Capture the complete approval screen.
4. Do not use copy/paste as proof of visual presence; record visual presentation separately.
5. Approve if prompted.
6. Submit: `List the available test tools. Do not call them.`
7. Capture the outbound request.
8. Run the code-point analyzer.
9. Record whether the client displayed a warning or escaped representation.

### Finding condition

`APPROVALTRACE_TAG_MARKER` decodes from TAG code points in M while the approval UI does not visibly or explicitly represent those code points.

### Safety

The marker contains no instruction and requests no sensitive action.

## 6. AT-003 — Nested schema visibility

### Goal

Determine whether nested security-relevant schema descriptions sent to M are represented in U.

### Procedure

1. Activate AT-003.
2. Reconnect the server.
3. Inspect the approval UI for:
   - `export_target`;
   - its type;
   - its description;
   - `NESTED_FIELD_PRESENT`.
4. Record whether expansion, hover, or a secondary details view is required.
5. Approve if required.
6. Submit: `List the available test tools and their parameters. Do not call them.`
7. Confirm whether `NESTED_FIELD_PRESENT` exists in M.

### Result guidance

- **PASS:** the nested field and material description are visibly available before approval.
- **PARTIAL:** the model receives the nested field but the UI shows only a name or partial structure.
- **FAIL:** the client represents the tool as materially narrower than the schema sent to the model.
- **INCONCLUSIVE:** the client does not send nested descriptions or the UI cannot be observed reliably.

## 7. AT-004 — Schema capability expansion

### Goal

Test whether adding a required destination and content-inclusion capability triggers renewed approval.

### Procedure

1. Activate AT-004 in `initial` phase.
2. Reconnect and complete initial approval.
3. Generate one baseline model request.
4. Save the baseline screenshot and request.
5. Change phase:

   ```http
   POST /approvaltrace/phase/mutated
   ```

6. Observe whether the client receives `notifications/tools/list_changed` and requests `tools/list` again.
7. Do not manually reconnect unless the client remains idle; document any forced action.
8. Trigger another model request with: `List the available test tools and parameters. Do not call them.`
9. Record warning, diff, and reapproval behavior.
10. Count model requests containing `export_target` before renewed approval.

### Pass criteria

- The changed schema is not supplied to the model before renewed approval; or
- the client uses a documented policy that displays and explicitly accepts the changed fields before use.

## 8. AT-005 — Notified description mutation

### Goal

Test standards-compliant dynamic tool metadata change.

### Procedure

1. Activate AT-005 in `initial` phase.
2. Complete initial approval and capture one baseline request.
3. Change to `mutated` phase.
4. Confirm the server emits `notifications/tools/list_changed` in server diagnostics.
5. Observe client refresh behavior.
6. Trigger a second request.
7. Search M for `APPROVALTRACE_MUTATED`.
8. Record whether renewed approval occurred before the first request containing that marker.

### Primary metric

`changed_requests_before_reapproval`

### Pass criteria

The metric is zero and the material change is represented to the user.

## 9. AT-006 — Silent mutation

### Goal

Measure the consequences of a server changing metadata without sending the optional list-changed notification.

### Procedure

1. Activate AT-006 in `initial` phase.
2. Complete initial approval and capture a baseline request.
3. Change to `mutated` phase.
4. Wait 5 seconds and confirm no list-changed notification was emitted.
5. Trigger another client interaction without restarting.
6. If the client does not refresh tool metadata, start a new chat while keeping the same client process.
7. If still unchanged, reconnect the MCP server and document that a reconnect was required.
8. Search M for `APPROVALTRACE_SILENT_MUTATION`.
9. Record whether prior approval was reused.

### Interpretation

This scenario does not treat failure to detect an unannounced in-session change as automatically non-compliant. Report separately:

- in-session behavior;
- new-chat behavior;
- reconnect behavior;
- whether changed metadata was used under the old approval.

## 10. Result classification

### PASS

Material model-bound metadata was represented before consent, and materially changed metadata was not used before renewed consent.

### PARTIAL

The client represented the basic tool but omitted some model-bound schema detail without creating a clearly contradictory security meaning.

### FAIL

At least one of the following was reproduced twice:

- hidden model-bound content was not visibly represented;
- a materially expanded schema reached the model before renewed approval;
- a processed tool-list change updated M without updating user consent;
- the approval UI communicated materially different capabilities from M.

### INCONCLUSIVE

The client could not be configured, capture was incomplete, UI evidence was unavailable, or provider-specific transformation prevented deterministic comparison.

## 11. Publication checklist

- [ ] Finding reproduced twice on a clean profile.
- [ ] Exact client version recorded.
- [ ] Raw evidence retained privately.
- [ ] Publication bundle redacted and manually reviewed.
- [ ] Evidence hashes verify.
- [ ] Screenshots contain no unrelated private data.
- [ ] Maintainer contacted for potential FAIL.
- [ ] Maintainer response included or response deadline documented.
- [ ] Result wording distinguishes UI limitation, conformance concern, and confirmed vulnerability.
