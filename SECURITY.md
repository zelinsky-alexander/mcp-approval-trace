# Security policy

MCP ApprovalTrace is a research harness intended for isolated test environments.

## Safe-use rules

- Use synthetic markers and synthetic files only.
- Do not configure production credentials in clients under test.
- Bind the capture API to loopback unless you intentionally isolate it.
- Review evidence bundles before publication; raw model requests can contain unrelated prompts.
- Do not test third-party hosted systems without authorization.

## Reporting a vulnerability

Open a private security advisory in this repository or contact the maintainer privately before public disclosure. Include a minimal reproduction, affected version, impact, and whether the issue exposes secrets from captured evidence.
