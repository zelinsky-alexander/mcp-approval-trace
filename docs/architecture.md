# Solution architecture

## 1. Purpose

MCP ApprovalTrace is a controlled research lab for testing a specific trust boundary:

> Does an MCP client show the user the same security-relevant tool metadata that it sends to its model provider, and does it obtain renewed approval before using materially changed metadata?

The project is intentionally not a production MCP gateway. It does not determine whether a server is malicious, inspect a tool's implementation, or prove how an LLM internally tokenizes or follows metadata. It creates reproducible evidence across three observable representations:

- **S — server-supplied representation:** the exact MCP tool definition emitted by the controlled server.
- **U — user-visible representation:** screenshots and structured observations of the client approval interface.
- **M — model-bound representation:** the exact tool metadata in the client's outbound OpenAI-compatible request.

The core comparison is `S ↔ M ↔ U`, with time added for mutation scenarios.

## 2. System context

```text
┌──────────────────────────────┐
│ Research operator            │
│                              │
│ - selects scenario           │
│ - observes approval UI       │
│ - records screenshots        │
└──────────────┬───────────────┘
               │ control API / observation file
               ▼
┌─────────────────────────────────────────────────────────────┐
│ ApprovalTrace lab                                            │
│                                                             │
│  ┌─────────────────────┐       ┌──────────────────────────┐ │
│  │ Mutation MCP server │       │ Model capture API        │ │
│  │ JSON-RPC over stdio │       │ OpenAI-compatible HTTP   │ │
│  └──────────┬──────────┘       └─────────────┬────────────┘ │
│             │                                 │              │
│             │ S                               │ M            │
│             ▼                                 ▼              │
│       ┌─────────────────────────────────────────────┐       │
│       │ Unmodified client under test                │       │
│       │ Continue, Cline, or another client profile  │       │
│       └─────────────────────────────────────────────┘       │
│                                                             │
│  ┌─────────────────────┐       ┌──────────────────────────┐ │
│  │ Differential        │──────▶│ Evidence bundle/report   │ │
│  │ analyzer            │       │ JSON, PNG, HTML, hashes  │ │
│  └─────────────────────┘       └──────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 3. Component architecture

### 3.1 Scenario-controlled mutation MCP server

Location: `mutation_server/`

The server implements the minimum MCP protocol surface needed by the research:

- `initialize`
- `notifications/initialized`
- `ping`
- `tools/list`
- `tools/call`
- `notifications/tools/list_changed`

It communicates through line-delimited JSON-RPC over standard input/output. No production data or external services are accessed. `tools/call` always returns a synthetic result.

Scenario state is read from `.approvaltrace/server-state.json`, or from the path specified by `APPROVALTRACE_STATE_FILE`. The capture/control API writes this state. A background watcher detects a transition from `initial` to `mutated` and emits `notifications/tools/list_changed` only when the active scenario specifies it.

This design supports two distinct temporal cases:

1. **Notified mutation:** the server changes metadata and sends the protocol notification.
2. **Silent mutation:** the metadata changes without a notification, allowing research into reconnect and cache behavior.

### 3.2 Scenario definitions

Location: `mutation_server/scenarios/`

Scenarios are YAML files containing:

- stable ID and title;
- initial tool definition;
- optional mutation patch;
- notification behavior;
- expected observable properties;
- a statement that real tool execution is not required.

The server uses deterministic deep merge for mutations. Special fixture values support controlled Unicode TAG encoding without embedding invisible source text directly into YAML:

```yaml
description:
  concat:
    - "Visible text."
    - tag_text: APPROVALTRACE_TAG_MARKER
```

This reduces accidental normalization by editors and makes the fixture auditable.

### 3.3 Model capture API

Location: `approvaltrace/capture_api/`

The FastAPI service exposes:

- `GET /v1/models`
- `POST /v1/chat/completions`
- `POST /v1/responses`
- `POST /approvaltrace/activate`
- `POST /approvaltrace/phase/{phase}`
- `GET /approvaltrace/state`
- `GET /approvaltrace/runs/{run_id}/captures`

The two model endpoints store the exact JSON request, calculate its SHA-256 digest, extract the `tools` array, write a redacted publication copy, and return a harmless canned response.

The API does not forward requests to an external model. Its role is to observe the last client-controlled representation before a model provider would receive it.

### 3.4 Manual approval observer

Location: `approvaltrace/observers/` and client profile checklists.

UI evidence is semi-manual in version 0.1 because approval interfaces are client-specific and automated desktop interaction can introduce brittle, non-reproducible behavior.

The observer records controlled categorical values:

- `full`
- `partial`
- `truncated`
- `absent`
- `not_applicable`
- `unable_to_determine`

The form records whether approval, warning, reapproval, or a visible diff appeared, along with screenshot paths and exact client/environment metadata.

### 3.5 Differential analyzer

Location: `approvaltrace/analyzer/`

The analyzer contains four deterministic layers:

1. **Canonicalization** — stable JSON serialization and hashes while retaining raw evidence.
2. **Code-point analysis** — narrow detection of Unicode TAG, zero-width, and bidirectional controls without treating normal non-ASCII languages as malicious.
3. **Schema path extraction** — deterministic flattening of security-relevant MCP fields.
4. **Representation comparison** — field-level comparison of server and model-bound tools, plus visibility classification using the observer record.

An LLM is not used to decide pass/fail. This makes results reproducible and reviewable.

### 3.6 Evidence bundle

Location: `approvaltrace/evidence/`

Each completed run can contain:

- scenario definition;
- server tool definition;
- raw and redacted model request;
- observer record;
- screenshots;
- field comparison;
- code-point findings;
- result classification;
- static HTML report;
- evidence manifest and SHA-256 file list.

The evidence manifest makes later file modification detectable. It is tamper-evident, not an identity or timestamping guarantee. Version 0.1 deliberately avoids blockchain, transparency logs, and remote signing services.

## 4. Temporal sequence

### 4.1 Baseline scenario

```text
Operator       Capture API       MCP server       Client       Approval UI
   | activate initial |              |               |              |
   |----------------->| write state  |               |              |
   |                  |------------->|               |              |
   |                  |              |<--initialize--|              |
   |                  |              |--tools/list-->|              |
   |                  |              |               |--display---->|
   |                  |<----------- model request ---|              |
   |                  | store M      |               |              |
   | record U ----------------------------------------------------->|
```

### 4.2 Mutation scenario

```text
Operator       Capture API       MCP server       Client       Approval UI
   | phase mutated  |                |               |              |
   |-------------->| update state   |               |              |
   |               |--------------->|               |              |
   |               |                |--list_changed>|              |  notified only
   |               |                |<--tools/list--|              |
   |               |                |--mutated tool>|              |
   |               |                |               |--reapprove?->|
   |               |<---------- changed model request ------------|
   |               | count changed requests before reapproval      |
```

The primary temporal metric is:

```text
changed_requests_before_reapproval
```

It counts outbound model requests containing materially changed tool metadata before renewed user approval was observed. It does not imply that a model followed the metadata or that a tool action occurred.

## 5. Trust boundaries

### Boundary A — controlled MCP server to client

The test server is trusted only as a deterministic fixture. Its output is preserved as S.

### Boundary B — client approval UI

The client decides which fields to display, truncate, normalize, or hide. ApprovalTrace treats the UI as evidence to observe, not as a source of truth.

### Boundary C — client to model provider

The local capture API observes M. HTTPS and provider internals are deliberately excluded because the test ends at the client request boundary.

### Boundary D — operator evidence handling

Screenshots and raw requests can expose unrelated information. Publication requires redaction and bundle review.

## 6. Security and privacy design

- The API binds to `127.0.0.1` by default.
- No model request is forwarded externally.
- Tool execution is synthetic.
- Known secret keys and home-directory paths are redacted from publication copies.
- Raw evidence is excluded from Git by default.
- Scenario markers are harmless fixed strings.
- Normal Hebrew, Arabic, Cyrillic, accented Latin, and emoji are not generically flagged.

Redaction is defense in depth, not a guarantee. The operator must inspect every public evidence bundle.

## 7. Deployment modes

### Local Windows research mode

- Python 3.12+
- VS Code with client extension
- capture API in PowerShell terminal
- MCP server spawned by the client using `python -m mutation_server.server`
- evidence under `.approvaltrace/`

### Reproducible container mode

Docker Compose runs the capture API for CI or API-level verification. Desktop clients normally run on the host and address the API through loopback or an explicitly mapped local address. The stdio MCP server should remain a host process when testing a desktop client.

## 8. Deliberate non-goals

Version 0.1 does not:

- classify malicious intent;
- evaluate model compliance with hidden instructions;
- attest the implementation of a remote MCP server;
- replace Interlock, MCPProxy, or an enterprise gateway;
- automate arbitrary desktop UIs;
- claim that every omitted field is a vulnerability;
- provide production blocking or quarantine.

## 9. Extension points

Future work can add:

- Anthropic- and Gemini-specific capture adapters;
- browser/desktop UI automation with captured DOM/accessibility trees;
- signed evidence bundles using Sigstore or Ed25519;
- new client profiles;
- richer schema-materiality rules;
- comparison against MCP gateways;
- integration with the official MCP conformance suite.
