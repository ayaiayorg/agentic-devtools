# Specification Quality Checklist: Split State Directory Race Condition

**Purpose**: Validate specification completeness before proceeding to planning
**Created**: 2026-05-11
**Feature**: [spec.md](../spec.md)
**Source Issue**: #1180

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

- [ ] All 10 functional requirements are listed explicitly and are individually testable.
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

## Content Quality

- [ ] CHK001 Each of the 5 user stories (US1–US5) focuses on user/operator value rather than implementation mechanics (e.g., US2 frames env var propagation as "child processes do not need to re-read
  the shared file").
- [ ] CHK002 All user stories follow the "As a [role], I want [goal] so that [benefit]" format with named roles (AI agent, developer).
- [ ] CHK003 All 10 functional requirements and 5 non-functional requirements have explicit priority labels (P1/P2 for FRs; NFR-001 through NFR-005).
- [ ] CHK004 Requirements FR-001 through FR-010 specify behavior constraints ("must", "must not") without prescribing specific class names, function signatures, or internal data structures beyond the
  public interfaces (`get_state_dir()`, `run_in_background()`, `setup_pull_request_review()`). Exception: FR-001 may prescribe `os.replace()` as the atomic-write mechanism because it defines an
  inter-process safety contract (not an internal implementation detail) — the atomicity guarantee is a behavioral requirement observable by concurrent processes.
- [ ] CHK005 The pin file JSON schema in FR-001 (`state_dir`, `workflow`, `created_utc`, `ttl_hours`) is specified as a contract, not an implementation detail — it defines the inter-process
  communication format without dictating internal code organization.

## Requirement Completeness

- [ ] CHK006 Each of the 5 user stories has at least two Given/When/Then acceptance criteria that are independently testable (e.g., US1 covers both the dual-flag and single-flag scenarios).
- [ ] CHK007 All 10 edge cases (env var non-existent directory, empty string, concurrent tasks, manual override, external bootstrap modification, worktree deletion, stale pin, moved/deleted pin
  target, concurrent review overwrite, corrupt pin content) have explicit expected behavior defined.
- [ ] CHK008 Acceptance scenarios for US3 reference the specific reproduction scenarios from issue #1180 (Scenario A and Scenario B) with measurable outcomes (zero duplicate directories).
- [ ] CHK009 Success criteria include quantifiable metrics: zero duplicate directories, 100% test coverage, all existing tests pass, race condition no longer reproducible.
- [ ] CHK010 Scope boundaries are explicit — Non-goals section excludes state system redesign, concurrent same-worktree workflows, bootstrap format changes for non-review workflows, and API layer
  modifications.
- [ ] CHK011 Dependencies on existing codebase are identified: affected files list names `state.py`, `background_tasks.py`, `review_commands.py`, and `workflows/commands.py` with specific functions.
- [ ] CHK012 The 5 clarifications (C1–C5) resolve ambiguities about atomic write mechanism, TTL renewal, logging level/destination, env var path constraints, and pin cleanup scope — each with an
  explicit answer applied to the relevant spec section.

## Feature Readiness

- [ ] CHK013 Each functional requirement (FR-001 through FR-010) has testable acceptance criteria derivable from the requirement text (e.g., FR-002's four-step priority chain can be verified by
  setting/unsetting each resolution source).
- [ ] CHK014 All 5 user scenarios (US1–US5) map to at least one acceptance criterion in the top-level "Acceptance criteria" section (e.g., US1 maps to criteria 1 and 2, US2 maps to criteria 5 and 6).
- [ ] CHK015 Success criteria include measurable outcomes: "zero duplicate directories", "100% test coverage", "all existing tests pass", "race condition no longer reproducible" — none are subjective.
- [ ] CHK016 The spec does not prescribe internal class hierarchies, module decomposition, or algorithm choices — implementation details are limited to the public contract (env var name, pin file
  schema, resolution priority chain, atomic write pattern).
- [ ] CHK017 The "Intentional global pinning" design decision in FR-001 explicitly documents the trade-off rationale (TTL bounds, explicit cleanup, non-goal of concurrent workflows) rather than
  leaving it as an implicit side effect.
- [ ] CHK018 The two open questions (synchronous `setup_pull_request_review()` refactoring and extending env var approach to all workflows) are flagged for resolution before or during planning, not
  left as hidden assumptions.
- [ ] CHK019 NFR-005 (Atomicity) defines session-level invariant ("once resolved, the value must not change for the duration of the workflow session") that is testable via concurrent command execution
  during a workflow.

## Notes

- This checklist was generated from the specification content for issue #1180
- Items marked incomplete require spec updates before proceeding to planning
- Sections 1–5 contain the original 34 checklist items preserved in full
- The Content Quality, Requirement Completeness, and Feature Readiness sections add spec-specific validation items (CHK001–CHK019)

---
*Generated by Copilot SDK (claude-opus-4.6)*
