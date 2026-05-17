# Feature Specification: LangChain-Based Pull Request Review Workflow (Parallel Path)

**Feature Branch**: `feature/1428/implement-langchain-based-pull`  
**Created**: 2026-05-15  
**Status**: Draft  
**Input**: GitHub Issue #1428 — Implement LangChain-based PR review workflow parallel to the existing review path  
**Source Issue**: #1428 (<https://github.com/ayaiayorg/agentic-devtools/issues/1428>)

## Overview

The repository needs a LangChain/LangGraph-backed pull request review workflow
that can run in parallel with the existing review implementation. The new path
must be explicitly selectable, preserve existing review-state compatibility, and
allow side-by-side evaluation before any future default switch.

## Problem Statement

Current PR review execution relies on the existing review path only. To evaluate
a LangChain-based approach safely, maintainers need a controlled way to route
review execution through a new implementation without disrupting current
workflows, commands, or artifacts.

## Goals

- Add an explicit routing mechanism to run PR review using LangChain/LangGraph.
- Keep current default behavior unchanged unless the new mode is explicitly enabled.
- Preserve compatibility with existing review artifacts and workflow progression.
- Support repeatable side-by-side comparison between existing and LangChain paths.
- Ensure failures in the new path are diagnosable and do not silently alter default behavior.

## Non-Goals

- Replacing the existing PR review implementation in this phase.
- Introducing a mandatory migration of existing review-state files.
- Changing unrelated workflows outside PR review execution routing.
- Adding new external service dependencies beyond what is required for LangChain path execution.

## Clarifications

### Session 2026-05-15

- Q: How should model/provider selection work for the LangChain path?
  → A: Reuse existing repository configuration/state conventions and allow explicit override through existing command options/state keys where applicable.
- Q: Must the new path reuse the same review-state schema?
  → A: Yes. The LangChain path must read/write compatible `review-state.json` structures so downstream commands continue to work.
- Q: Should model parameters differ between existing and LangChain paths?
  → A: They may differ internally, but user-facing configuration and expected review output structure must remain consistent.

### Session 2026-05-15 (Ambiguity Scan)

- Q: What is the exact selection mechanism for opting into LangChain mode — a CLI flag, a state key, or an environment variable? → A: A state key (`review.engine` set to `"langchain"`) is the primary
  mechanism, consistent with existing `agdt-set` patterns. Additionally, the `agdt-initiate-pull-request-review-workflow` command shall accept an optional `--engine langchain` CLI flag that writes the
  state key before execution. The default value when unset is `"default"` (existing path). Environment variable `AGDT_REVIEW_ENGINE` may override the state key for CI/pipeline contexts.
- Q: What specific LangChain/LangGraph package versions are required, and should they be mandatory or optional dependencies? → A: `langchain-core>=0.3,<1.0` and `langgraph>=0.4,<1.0` shall be declared
  as optional extras (`pip install agentic-devtools[langchain]`). These packages are already used by the existing `agentic_devtools/orchestration/` module for the work-on-issue workflow, so version
  alignment with those existing constraints is required.
- Q: On a mid-run LangChain failure after partial artifact writes, should the system roll back artifacts or leave them in place for debugging? → A: Leave partial artifacts in place. The review-state
  file shall record a `"failed"` status on the session entry so that reruns can detect and resume or overwrite the incomplete session. No automatic rollback is performed; this matches existing path
  behavior where partial writes persist.
- Q: Should the new LangChain review graph live in the existing `agentic_devtools/orchestration/` module or in a new dedicated module? → A: Create a new subpackage
  `agentic_devtools/orchestration/review/` to house the PR review graph, keeping it separate from the work-on-issue graph in `orchestration/pilot_workflow.py`. Shared utilities (e.g., checkpointing,
  state schema patterns) may be imported from the parent `orchestration/` package.
- Q: What measurable bound applies to NFR-003 (startup overhead) for the LangChain path? → A: LangChain-mode startup overhead (from command invocation to first LLM call) shall not exceed 5 seconds on
  a standard development machine, excluding network latency. This is measured as the delta between LangChain-mode and existing-mode startup times.

## User Stories

### US-001 [P1]: Select LangChain review path explicitly

As a maintainer, I want an explicit command/workflow switch for LangChain review so that I can opt in safely without changing the default review behavior.

#### Acceptance Scenarios (Given/When/Then)

1. **Explicit opt-in routing via CLI flag**
   - Given a PR review command invocation with `--engine langchain`
   - When the review run starts
   - Then the system sets `review.engine` to `"langchain"` in state and routes execution to the LangChain/LangGraph implementation
   - And reports the routing choice (engine=langchain) in output/logs

2. **Explicit opt-in routing via state key**
   - Given `review.engine` is set to `"langchain"` via `agdt-set review.engine langchain`
   - When the PR review command is invoked without `--engine`
   - Then the system routes execution to the LangChain/LangGraph implementation

3. **Environment variable override**
   - Given `AGDT_REVIEW_ENGINE=langchain` is set in the environment
   - When the PR review command is invoked without `--engine` and without a `review.engine` state key
   - Then the system routes execution to the LangChain/LangGraph implementation

4. **Default path unchanged**
   - Given a PR review command invocation without LangChain mode enabled (no `--engine` flag, no `review.engine` state key, no `AGDT_REVIEW_ENGINE` env var)
   - When the review run starts
   - Then the existing review path is used
   - And no LangChain-specific behavior is activated

### US-002 [P1]: Preserve workflow compatibility

As a maintainer, I want the LangChain review path to produce compatible review-state artifacts so that existing follow-up commands continue to function.

#### Acceptance Scenarios (Given/When/Then)

1. **Compatible artifacts**
   - Given a PR reviewed via LangChain mode
   - When review artifacts are generated/updated
   - Then artifact locations and required schema fields remain compatible with existing consumers
   - And the `review-state.json` file is readable by all existing review lifecycle commands (`agdt-approve-file`, `agdt-request-changes`, `agdt-submit-file-review`, etc.)

### US-003 [P2]: Compare outcomes between both paths

As a maintainer, I want to run the existing and LangChain paths on similar PRs so that I can evaluate quality, reliability, and operational trade-offs.

#### Acceptance Scenarios (Given/When/Then)

1. **Side-by-side execution support**
   - Given two review runs where one uses the existing path and one uses LangChain mode
   - When results are inspected
   - Then both runs expose equivalent high-level statuses and actionable outputs
   - And both produce review-state files with the same schema and required fields

### US-004 [P3]: Diagnose failures quickly

As a maintainer, I want clear failure messaging for LangChain routing and execution errors so that I can recover quickly without breaking normal review operations.

#### Acceptance Scenarios (Given/When/Then)

1. **Actionable errors — missing dependencies**
   - Given LangChain mode is requested but `langchain-core` or `langgraph` packages are not installed
   - When the review run fails
   - Then the error message identifies the missing package(s) and suggests `pip install agentic-devtools[langchain]`
   - And the system does not silently switch to the default mode

2. **Actionable errors — missing configuration**
   - Given LangChain mode is requested but required model/provider configuration is absent
   - When the review run fails
   - Then the error message identifies the missing configuration key(s) and recovery action
   - And the system does not silently switch to a different mode

## Functional Requirements

### FR-001: Explicit LangChain selection

The PR review entrypoint shall provide an explicit mechanism to select the LangChain/LangGraph review path. The primary mechanism is the `review.engine` state key (value `"langchain"`). The
`agdt-initiate-pull-request-review-workflow` command shall accept an optional `--engine` CLI flag that writes this state key. The environment variable `AGDT_REVIEW_ENGINE` shall serve as a fallback
override when neither the CLI flag nor the state key is set. Resolution priority: CLI flag > state key > environment variable > default (`"default"`).

### FR-002: Default behavior preservation

When LangChain selection is not enabled (no `--engine` flag, no `review.engine` state key set to `"langchain"`, no `AGDT_REVIEW_ENGINE` env var), the PR review workflow shall execute the existing
implementation exactly as before.

### FR-003: Deterministic routing

When LangChain selection is enabled, the workflow shall deterministically route to the LangChain implementation and indicate the selected route in command output/logging (e.g., `[review-engine:
langchain]`).

### FR-004: Review-state schema compatibility

The LangChain path shall read and write review-state data compatible with the existing `review-state.json` schema and required fields. Partial writes from failed LangChain runs shall record a
`"failed"` status on the session entry to enable detection and recovery on reruns.

### FR-005: Artifact path compatibility

The LangChain path shall continue using existing artifact directory conventions (review prompts/queue/state under `pull-request-review/<commit_hash_short>/`) so dependent commands and workflows can
locate artifacts without changes.

### FR-006: Equivalent review lifecycle integration

The LangChain path shall integrate with existing review lifecycle commands (file approval, change requests, summary updates) without requiring a separate command surface. Commands such as
`agdt-approve-file`, `agdt-request-changes`, `agdt-request-changes-with-suggestion`, and `agdt-submit-file-review` shall operate identically regardless of which engine produced the review state.

### FR-007: Configuration compatibility

The LangChain path shall support model/provider configuration via existing repository configuration/state patterns (`.agdt/config/review-models.json` and `review-models-override.json`) and shall not
require a breaking change to current setup.

### FR-008: Dependency preflight validation

When LangChain mode is requested, the workflow shall validate that `langchain-core` and `langgraph` packages are importable and that required model/provider configuration is present before executing
the review graph. If validation fails, the command shall exit with code 1 and an actionable error message (e.g., `"LangChain packages not installed. Run: pip install agentic-devtools[langchain]"`).

### FR-009: Failure isolation

LangChain execution failures shall not mutate the `review.engine` state key or default-path routing behavior for future runs; subsequent runs without LangChain selection shall continue to use the
existing path. Partial artifact writes from failed runs shall persist for debugging but shall be marked with a `"failed"` session status.

### FR-010: Observability

The system shall emit clear logs/status markers indicating mode selection (engine value), review progress milestones, and terminal status for LangChain runs. Log entries shall be prefixed or tagged
with `[langchain]` to distinguish them from default-path logs.

### FR-011: Automated verification

Test coverage shall include routing behavior, default-path preservation, and at least one LangChain-mode success and failure-path validation scenario. Tests for the LangChain path shall use the
optional-dependency guard pattern (skip if `langchain-core`/`langgraph` not installed) to avoid breaking CI when extras are not present.

## Non-Functional Requirements

### NFR-001: Backward compatibility

Existing PR review commands and workflows shall remain fully backward compatible for users who do not opt into LangChain mode. No existing CLI command signatures, state key semantics, or artifact
schemas shall change.

### NFR-002: Reliability

LangChain-mode review runs should complete with reliability comparable to the existing path under equivalent conditions. Failed runs shall record a `"failed"` session status and shall not corrupt
existing review-state data.

### NFR-003: Performance

LangChain-mode startup overhead (from command invocation to first LLM API call) shall not exceed 5 seconds on a standard development machine, excluding network latency. This is measured as the delta
between LangChain-mode and existing-mode startup times for the same PR.

### NFR-004: Security

LangChain integration shall preserve existing secret-handling and logging safety expectations, including avoiding sensitive-token leakage in outputs. LangChain callbacks/tracers shall not emit PAT
values, API keys, or other credentials to logs or stdout.

### NFR-005: Maintainability

The LangChain review graph shall reside in a dedicated subpackage (`agentic_devtools/orchestration/review/`) separate from the work-on-issue graph. Routing and implementation boundaries should be
clear enough to support future default-switch or rollback decisions with minimal refactoring. Shared utilities (checkpointing, state schema patterns) may be imported from the parent `orchestration/`
package.

### NFR-006: Determinism

Given identical inputs/configuration, routing decisions and artifact schema outputs should be deterministic across repeated runs. The engine resolution priority (CLI flag > state key > environment
variable > default) shall produce the same routing decision for the same input combination.

## Acceptance Criteria

### AC-001

Given LangChain mode is requested (via `--engine langchain`, `review.engine` state key, or `AGDT_REVIEW_ENGINE` env var), when a PR review starts, then execution is routed to the LangChain path and
the route is reported in command output.

### AC-002

Given LangChain mode is not requested, when a PR review starts, then the existing review path runs unchanged.

### AC-003

Given a LangChain-mode review completes, when review artifacts are examined, then required review-state schema compatibility is preserved and artifacts are located in the standard
`pull-request-review/<commit_hash_short>/` directory.

### AC-004

Given LangChain-mode review data is produced, when follow-up review commands run (`agdt-approve-file`, `agdt-request-changes`, `agdt-submit-file-review`), then they operate without requiring
mode-specific command changes.

### AC-005

Given LangChain mode is requested with missing prerequisites (packages not installed or configuration absent), when execution begins, then the command fails fast with exit code 1, actionable error
output, and no silent fallback to the default engine.

## Success Criteria

- **SC-001:** 100% of non-opt-in PR review runs continue using the existing path after LangChain support is introduced.
- **SC-002:** 100% of explicit LangChain opt-in runs report LangChain routing in command output/logs.
- **SC-003:** At least one validated side-by-side evaluation run demonstrates schema-compatible artifacts between existing and LangChain paths.
- **SC-004:** LangChain preflight/dependency failures produce actionable error messages in 100% of tested failure scenarios.
- **SC-005:** Automated tests cover routing/default-preservation behavior and pass in CI for the implemented scope.

## Edge Cases

- **Missing runtime packages**: LangChain mode is requested but `langchain-core` or `langgraph` packages are unavailable in the runtime environment. The system shall fail with an actionable error
  suggesting `pip install agentic-devtools[langchain]` and shall not fall back to the default engine.
- **Missing model/provider configuration**: LangChain mode is requested while required model/provider configuration (e.g., `.agdt/config/review-models.json`) is missing or contains invalid entries.
  The system shall fail with an error identifying the specific configuration issue.
- **Cross-engine resume**: An in-progress `review-state.json` file created by the existing path is resumed/updated via the LangChain path. The LangChain path shall read the existing state and continue
  operating on it, preserving all existing entries. A new session entry shall be appended with the `"langchain"` engine identifier.
- **Mid-run failure with partial writes**: LangChain-mode execution fails mid-run after partial artifact writes. Partial artifacts shall remain on disk for debugging. The session entry in
  `review-state.json` shall be marked with `"failed"` status. Reruns shall detect the failed session and either resume or create a new session, and routing behavior shall remain explicit (no silent
  fallback).
- **Conflicting engine signals**: Both `--engine default` CLI flag and `AGDT_REVIEW_ENGINE=langchain` env var are set simultaneously. Resolution follows the documented priority order: CLI flag wins,
  so the default engine is used.

## User Scenarios & Testing

### Scenarios

- **US-001 [P1]:** Maintainer selects LangChain review path explicitly via CLI flag, state key, or environment variable; default path remains unchanged when no opt-in is present.
- **US-002 [P1]:** LangChain review path produces review-state artifacts compatible with all existing review lifecycle commands.
- **US-003 [P2]:** Maintainer runs existing and LangChain paths on comparable PRs for side-by-side quality evaluation.
- **US-004 [P3]:** LangChain routing and execution failures surface actionable error messages without silently altering default behavior.

### Testing Strategy

- **Routing tests:** Verify engine resolution priority (CLI flag > state key > env var > default) routes to the correct implementation for every combination.
- **Default-preservation tests:** Confirm that PR review without any LangChain opt-in produces identical behavior and artifacts to the pre-change baseline.
- **Schema-compatibility tests:** Validate that `review-state.json` written by the LangChain path is accepted by `agdt-approve-file`, `agdt-request-changes`, `agdt-request-changes-with-suggestion`,
  and `agdt-submit-file-review`.
- **Dependency-preflight tests:** Confirm actionable error (exit code 1) when `langchain-core` or `langgraph` is not importable, and when required model/provider configuration is missing.
- **Failure-isolation tests:** Verify that a failed LangChain run records `"failed"` session status, does not mutate `review.engine`, and does not corrupt existing review-state data.
- **Optional-dependency guard:** All LangChain-path tests use `pytest.importorskip` (or equivalent) so CI passes when extras are not installed.
- **Side-by-side artifact comparison:** At least one integration-level test confirms both engines produce structurally equivalent `review-state.json` output for the same PR input.

## Requirements

### Functional

- **FR-001:** Explicit LangChain selection via `review.engine` state key, `--engine` CLI flag, or `AGDT_REVIEW_ENGINE` env var with resolution priority CLI > state > env > default.
- **FR-002:** Default behavior preservation — existing path unchanged when LangChain is not selected.
- **FR-003:** Deterministic routing with engine choice reported in output/logs.
- **FR-004:** Review-state schema compatibility; failed sessions recorded with `"failed"` status.
- **FR-005:** Artifact path compatibility under `pull-request-review/<commit_hash_short>/`.
- **FR-006:** Equivalent review lifecycle integration — existing commands operate identically regardless of engine.
- **FR-007:** Configuration compatibility via existing `.agdt/config/review-models.json` patterns.
- **FR-008:** Dependency preflight validation with actionable error on missing packages or configuration.
- **FR-009:** Failure isolation — LangChain failures do not mutate routing state or default behavior.
- **FR-010:** Observability — `[langchain]`-prefixed log entries for mode selection, progress, and terminal status.
- **FR-011:** Automated verification with optional-dependency guard pattern for CI compatibility.

### Non-Functional

- **NFR-001:** Full backward compatibility for non-opt-in users.
- **NFR-002:** Reliability comparable to existing path; failed runs record status without corrupting state.
- **NFR-003:** ≤ 5 s startup overhead delta (LangChain vs existing) excluding network latency.
- **NFR-004:** No credential leakage through LangChain callbacks/tracers.
- **NFR-005:** Dedicated `agentic_devtools/orchestration/review/` subpackage with clear routing boundaries.
- **NFR-006:** Deterministic routing and artifact schema output for identical inputs.

---
*Generated by Copilot SDK (claude-opus-4.6)*
