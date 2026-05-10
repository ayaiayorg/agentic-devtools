# Requirements Quality Checklist: Split State Directory Race Condition

Use this checklist to review the requirements/spec quality for `1180-split-state-directory-during`.
Mark each item as complete only when the spec is explicit, internally consistent, and reviewable
without guessing.

## 1. Problem definition and scope

- [ ] The spec clearly defines the race condition in `runtime-bootstrap.json` access.
- [ ] The spec identifies both reproduction scenarios (A: both flags, B: single flag).
- [ ] The spec explains the root cause: shared mutable file without synchronization.
- [ ] The spec defines what is in scope (environment variable propagation, state directory
  consistency) and what is out of scope (state system redesign, concurrent workflows).
- [ ] The spec lists the affected files and functions.

## 2. User needs and success criteria

- [ ] All 5 user stories are present and written from a user or operator perspective.
- [ ] Each user story has a concrete outcome that can be validated in review or tests.
- [ ] The spec explains how users benefit from consistent state directory resolution.
- [ ] The spec makes clear what "successful fix" looks like (zero duplicate directories).
- [ ] Success criteria are stated in measurable terms (zero duplicates, 100% coverage, all
  tests pass).

## 3. Functional requirements

- [ ] All 9 functional requirements are listed explicitly and are individually testable.
- [ ] Each functional requirement uses clear normative language ("must", "must not").
- [ ] The environment variable resolution priority is described unambiguously
  (`AGENTIC_DEVTOOLS_STATE_DIR` → pin file (if present/valid) → bootstrap file → fallback).
- [ ] The spec states that `AGENTIC_DEVTOOLS_STATE_DIR` bypasses both the pin file and
  `runtime-bootstrap.json` (preserving O(1) / no-pin/bootstrap-file-reads guarantee).
- [ ] The spec defines pin file validation rules (FR-003): existence check, directory safety,
  TTL expiration, workflow name match, and JSON parse validity.
- [ ] The spec states what causes `setup_pull_request_review()` to skip bootstrap modification.
- [ ] The spec states what happens when `AGENTIC_DEVTOOLS_STATE_DIR` is set vs. not set.
- [ ] The spec states how background tasks inherit the environment variable.
- [ ] The spec defines diagnostic logging requirements for resolution path tracking.

## 4. Edge cases and failure handling

- [ ] All 10 edge cases are explicitly enumerated.
- [ ] The spec covers behavior when the environment variable points to a non-existent directory.
- [ ] The spec covers behavior when the environment variable is empty.
- [ ] The spec covers behavior when multiple background tasks run concurrently.
- [ ] The spec covers behavior when the bootstrap file is modified externally.
- [ ] The spec defines failure behavior that is consistent with existing workflow expectations.
- [ ] The spec covers stale/stray pin file scenarios (workflow crash, expired TTL).
- [ ] The spec covers pin file pointing to a moved/deleted directory.
- [ ] The spec covers concurrent review start overwriting an existing pin.
- [ ] The spec covers invalid/corrupt pin file content.

## 5. Non-functional requirements

- [ ] All 5 non-functional requirements are explicitly documented.
- [ ] Performance expectation (O(1) resolution) is stated clearly.
- [ ] Cross-platform safety is addressed for Windows, macOS, and Linux.
- [ ] Test coverage requirement (100%) matches the project's existing policy.
- [ ] Backward compatibility requirement is explicit for non-review workflows.
