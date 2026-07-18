# Contributing

Contributions are welcome for new client profiles, deterministic scenarios, evidence validators, and documentation.

1. Create a focused branch.
2. Add or update tests.
3. Run `pytest` and `ruff check .`.
4. Do not commit private captures, tokens, usernames, or unrelated conversation data.
5. For a new client result, include the exact client version, OS, configuration hash, observation form, and redacted evidence bundle.

Findings about a shipping client should follow `docs/responsible-disclosure.md` before being added to public result tables.
