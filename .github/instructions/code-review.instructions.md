---
applyTo: "**"
---

# Custom Review Instructions

MUST NOT comment on:

- CI check failures (linting, formatting, type errors, test failures)
- Potential markdownlint violations (MD013, line length, etc.)
- Code formatting issues enforced by automated tools (ruff, black, prettier)
- Import ordering (enforced by ruff/isort)

All CI-enforced checks are verified GREEN before review is requested.
Comments about these areas waste compute cycles on false positives.

Focus exclusively on:

- Logic correctness and potential bugs
- Security vulnerabilities
- Architecture and design issues
- Code clarity and maintainability
- Missing edge case handling
- API contract violations
- Race conditions and concurrency issues
