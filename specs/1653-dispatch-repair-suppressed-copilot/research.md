# Research Notes: Suppressed Copilot Review Comments

## Decision 1: Source of Suppressed Feedback

- Chosen source: review body HTML `<details>` block in the Copilot review payload.
- Rationale: suppressed low-confidence feedback is embedded there and not reliably exposed as standalone REST review comments.

## Decision 2: Parsing Approach

- Chosen approach: stdlib `re` parsing in `github_provider.py` (no new dependency).
- Rationale: constrained HTML shape and low complexity make a lightweight parser sufficient; failures can be handled with fail-soft behavior.

## Decision 3: Deduplication Semantics

- Chosen approach: exact match after normalization (path/body only).
- Rationale: deterministic behavior and avoids false-positive collapsing from substring heuristics.

## Decision 4: Synthetic ID Strategy

- Chosen approach: assign unique negative sentinel IDs to recovered suppressed entries.
- Rationale: avoids ID collisions and prevents synthetic entries from masquerading as real GitHub DB IDs.

## Decision 5: Downstream Safety

- Chosen approach: add explicit `is_suppressed` guards in ID-keyed evaluator flows.
- Rationale: synthetic suppressed entries have no real GitHub thread and must not be sent to thread-resolution APIs.
