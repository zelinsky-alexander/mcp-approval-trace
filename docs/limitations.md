# Limitations

- UI evidence is initially semi-manual and may contain observer error.
- OpenAI-compatible capture does not cover clients locked to other provider protocols.
- The project observes outbound requests, not provider internals or LLM tokenization.
- A missing field in an approval UI is not automatically a vulnerability.
- Silent mutation behavior depends on when a client refreshes `tools/list`.
- The test server is intentionally minimal and may not exercise every MCP extension.
- Evidence manifests detect modification but do not prove author identity or trusted time.
- Redaction cannot guarantee removal of every private value; manual review remains mandatory.
