# Continue client profile

This profile documents a repeatable Continue test setup. Continue configuration formats change; record the exact extension version and preserve a sanitized configuration copy with each published result.

## Model endpoint

Configure an OpenAI-compatible model using:

- Base URL: `http://127.0.0.1:8741/v1`
- Model: `approvaltrace-capture`
- API key: `approvaltrace-local`

## MCP server

Configure one stdio server:

```text
command: python
args: -m mutation_server.server
```

Set the environment variables described in the repository README.

## Run controls

Before every scenario:

1. Use a fresh Continue profile or document reused state.
2. Disable all unrelated tools and MCP servers.
3. Activate a unique ApprovalTrace run ID.
4. Restart the MCP connection.
5. Follow `observer-checklist.yaml` and `docs/test-protocol.md`.

Do not publish a result if Continue transforms the request into a provider format the capture API cannot deterministically parse; classify it as `INCONCLUSIVE` and preserve the raw evidence privately.
