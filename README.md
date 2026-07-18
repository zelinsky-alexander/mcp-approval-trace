# MCP ApprovalTrace

**A reproducible conformance lab for comparing MCP tool metadata shown to users with the exact metadata sent in model-bound API requests.**

## Research question

> Does an MCP client obtain meaningful approval for the same security-relevant tool metadata it supplies to its model provider, and does it renew that approval when the metadata changes?

ApprovalTrace measures three representations:

- **S:** metadata supplied by a controlled MCP server;
- **U:** metadata represented in the client approval interface;
- **M:** metadata included in the client's outbound model request.

It then evaluates `S ↔ M ↔ U` across clean, concealed-metadata, schema-visibility, and temporal mutation scenarios.

## What is included

- A dependency-light MCP JSON-RPC/stdio mutation server.
- Six deterministic scenarios, AT-001 through AT-006.
- A local OpenAI-compatible capture API for Chat Completions and Responses requests.
- Unicode control-character and nested-schema analysis.
- Field-level server-to-model comparison.
- Structured manual approval observations.
- Static HTML evidence reports and SHA-256 manifests.
- Automated unit and integration tests.
- Exact manual test protocol for Continue and Cline profiles.

## What this project does not claim

- It does not discover MCP tool poisoning or Unicode TAG concealment.
- It does not determine whether a server is malicious.
- It does not evaluate whether a model follows hidden metadata.
- It does not replace an MCP security gateway.
- It does not attest remote server implementation or behavior.

See [Prior art](docs/prior-art.md) and [Limitations](docs/limitations.md).

## Architecture

The complete design, trust boundaries, data flows, temporal sequence, and evidence model are documented in [docs/architecture.md](docs/architecture.md).

```text
controlled MCP server ──S──▶ real client ──M──▶ local capture API
                                 │
                                 U
                                 ▼
                         approval UI evidence

                     deterministic comparison
                                 ▼
                    JSON + screenshots + HTML
```

## Scenarios

| ID | Scenario | Measurement |
|---|---|---|
| AT-001 | Clean baseline | Validate the capture path and negative control |
| AT-002 | Unicode TAG marker | Check whether concealed model-bound metadata is visibly represented |
| AT-003 | Nested schema visibility | Compare nested parameter descriptions in U and M |
| AT-004 | Schema capability expansion | Test reapproval after adding required sensitive-looking parameters |
| AT-005 | Notified mutation | Test handling of `notifications/tools/list_changed` |
| AT-006 | Silent mutation | Measure refresh and prior-approval reuse without notification |

The normative step-by-step procedure and pass/fail rules are in [docs/test-protocol.md](docs/test-protocol.md).

## Quick start

### 1. Create an environment

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Linux/macOS:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

### 2. Run automated tests

```bash
pytest
```

### 3. Start the local capture API

```bash
approvaltrace capture-api --root .approvaltrace
```

The OpenAI-compatible base URL is:

```text
http://127.0.0.1:8741/v1
```

### 4. Configure the MCP server in the client

Command:

```text
python -m mutation_server.server
```

Environment:

```text
PYTHONPATH=<absolute repository path>
APPROVALTRACE_STATE_FILE=<absolute repository path>/.approvaltrace/server-state.json
APPROVALTRACE_SCENARIO_DIR=<absolute repository path>/mutation_server/scenarios
```

Client-specific setup is documented in:

- [Continue profile](client_profiles/continue/README.md)
- [Cline profile](client_profiles/cline/README.md)

### 5. Activate a run

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8741/approvaltrace/activate `
  -ContentType application/json `
  -Body '{"run_id":"continue-at001-001","scenario_id":"AT-001","phase":"initial"}'
```

Mutation phase:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8741/approvaltrace/phase/mutated
```

### 6. Record UI evidence

Copy the relevant `observer-checklist.yaml` into the run directory, complete it, and save approval screenshots. Do not commit unreviewed raw captures.

## Evidence format

A publishable run should contain:

```text
environment.json
scenario.yaml
server-tool.json
model-request.redacted.json
observer.yaml
approval-before.png
approval-after.png
field-comparison.json
codepoints.json
findings.json
evidence-manifest.json
evidence.sha256
report.html
```

Verify a bundle:

```bash
approvaltrace verify results/published/<client>/<version>/<scenario>/<run>
```

## Result language

- **PASS:** material model-bound metadata was represented and changed metadata was not used before renewed approval.
- **PARTIAL:** some model-bound schema detail was not fully visible without a clearly contradictory security meaning.
- **FAIL:** a defined failure condition was reproduced twice with complete evidence.
- **INCONCLUSIVE:** capture, UI evidence, or provider transformation prevented deterministic assessment.

## Publication workflow

1. Reproduce a potential failure twice on a clean profile.
2. Review and redact the public bundle.
3. Verify all hashes.
4. Follow [responsible disclosure](docs/responsible-disclosure.md).
5. Add the redacted bundle under `results/published/`.
6. Generate a static report for GitHub Pages or your security site.

## Development

```bash
pytest
ruff check .
```

The GitHub Actions workflow runs both commands on Python 3.12 and 3.13.

## License

Apache-2.0.
