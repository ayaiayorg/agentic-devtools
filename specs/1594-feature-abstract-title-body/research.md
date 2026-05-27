# Research: Abstract PR Title/Body Change Event Filtering

## Decision Summary

- Add provider-agnostic edit metadata fields to `EventPayload`.
- Parse edit-change details in providers where available.
- Apply a pure preflight guard in `ai_pr_loop_command()` to skip irrelevant edited events.

## Rationale

- Keeps workflow logic simple and centralized in Python.
- Preserves fail-open behavior when edit-change metadata is unavailable.
- Avoids unnecessary CI work for body-only edits while allowing title/base edits to continue.
