# Cline client profile

This profile documents a repeatable Cline test setup. Record the exact VS Code and Cline extension versions for every run.

## Model endpoint

Select an OpenAI-compatible provider and set:

- Base URL: `http://127.0.0.1:8741/v1`
- Model ID: `approvaltrace-capture`
- API key: `approvaltrace-local`

## MCP server

Add a single stdio MCP server that launches:

```text
python -m mutation_server.server
```

Set absolute values for `PYTHONPATH`, `APPROVALTRACE_STATE_FILE`, and `APPROVALTRACE_SCENARIO_DIR`.

## Observation

Cline can expose tool details at more than one interaction point. Record separately:

- server installation or enablement consent;
- tool-call approval;
- any expandable tool-schema view;
- warnings or diffs after metadata mutation.

Follow the exact procedure in `docs/test-protocol.md` rather than interpreting normal tool-call confirmation as renewed metadata approval.
