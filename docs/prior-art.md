# Prior art and project boundary

ApprovalTrace does not claim discovery of MCP tool poisoning, Unicode TAG concealment, or post-approval rug-pull attacks.

Important adjacent work includes:

- Unicode TAG-block concealment and approval-view fidelity research: arXiv:2607.05744.
- MCPSecBench and other MCP security benchmarks.
- The official MCP conformance project.
- MCPProxy tool hashing and quarantine.
- Interlock post-approval drift and behavioral trust controls.
- Research on tool poisoning across AI-assisted development clients.

ApprovalTrace targets a narrower measurement gap: a reproducible black-box comparison of an unmodified shipping client's approval representation with its exact model-bound tool metadata, including a temporal reapproval metric.

Prior-art claims should be rechecked before every publication because MCP security tooling is developing rapidly.
