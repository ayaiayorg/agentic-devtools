# Feature Specification: Abstract PR Title/Body Change Event Filtering as a Provider-Agnostic Guard

**Feature Branch**: `speckit/1594/phase-1-specify`  
**Created**: 2026-05-26  
**Status**: Draft  
**Input**: User description: "Abstract PR title/body change event filtering as a provider-agnostic guard"  
**Source Issue**: #1594 (<https://github.com/ayaiayorg/agentic-devtools/issues/1594>)

## Problem Statement

The ai-pr-loop workflow currently triggers on various `pull_request` event types, but it lacks the ability to distinguish between meaningful title changes (such as removing a `[WIP]` prefix) and
irrelevant body-only edits. When a PR title changes, guards like the WIP-title check must be re-evaluated because the PR may have transitioned from a blocked state to an actionable one. However, when
only the PR body is edited, the entire orchestration pipeline fires unnecessarily, consuming CI minutes and generating noise without any possible state change in the guard evaluation.

Today, the only way to filter these events is through GitHub Actions workflow-level `if:` conditions written in YAML. This approach is inherently platform-specific — it ties filtering logic to
GitHub's event schema (`github.event.changes.title`) and cannot be reused when the ai-pr-loop runs on Azure DevOps or other CI platforms. The `EventPayload` dataclass currently has no fields that
convey what specifically changed during an `edited` event, so the orchestrator cannot make this determination in Python.

The core problem is twofold. First, the orchestrator lacks the metadata needed to determine whether an `edited` event warrants a full pipeline run. Second, because this metadata is absent from the
provider-agnostic `EventPayload` model, there is no clean way to implement the filtering without coupling the orchestrator to a specific CI platform's raw event schema.

This feature introduces three fields on the `EventPayload` model: `title_changed`
and `body_changed` (both default `False`), plus `edit_changes_known` (default
`False`) to indicate whether the provider had reliable per-field change metadata.
A new edit-relevance guard runs before all existing guards and short-circuits
`pull_request` `edited` events when `edit_changes_known=True` and
`title_changed=False` (body-only or other non-title edits).
This approach keeps the YAML triggers minimal (simply adding `edited` to the
event list), moves filtering into testable Python, and works identically across
all supported CI providers.

## Clarifications

### Session 2026-05-26

- Q: Where exactly should the edit-relevance preflight live — as a standalone function in `guards.py`, or inline in `run_ai_pr_loop()` in `orchestrator.py`? → A: It should be implemented as a
  standalone function in `agentic_devtools/cli/ci/guards.py` (e.g., `check_edit_relevance(event: EventPayload) -> tuple[bool, str]`) for testability, but invoked inline in `run_ai_pr_loop()`
  immediately after event parsing and before lock acquisition or `build_pr_state_snapshot()`. This keeps it consistent with the existing guard pattern while respecting the spec's requirement that it
  runs before any network calls.

- Q: The spec says the guard exits with code 0 when skipping — should this use `EXIT_SUCCESS` (0) or a new dedicated exit code (e.g., `EXIT_EDIT_SKIPPED = 6`) so CI workflows can distinguish "nothing
  to do" from "intentionally skipped due to irrelevant edit"? → A: Use `EXIT_SUCCESS` (0). The edit-relevance skip is a normal, expected outcome — not an error or special condition. The INFO log
  message provides sufficient observability for distinguishing skips from other exit-0 cases. Adding a new exit code would complicate workflow YAML for no practical benefit.

- Q: For the `label` field changes in a PR `edited` event (e.g., milestones or assignees changed via the API triggering an `edited` action), should `edit_changes_known` be `True` even when neither
  title nor body keys are in the `changes` dict? → A: Yes. When the `changes` key is present in the payload (even if it contains neither `title` nor `body` — e.g., only `base` or other fields),
  `edit_changes_known` should be set to `True`. This correctly signals that the provider had metadata and confidently determined that no title change occurred, allowing the guard to skip. This is
  already specified in the edge cases section and FR-002.

- Q: The spec mentions the pipeline `command.py` (`run_ai_pr_loop_v2`) as a newer entry point alongside the legacy `orchestrator.py` (`run_ai_pr_loop`). Should the edit-relevance preflight be
  implemented in both entry points or only one? → A: The edit-relevance preflight should be implemented in the legacy `run_ai_pr_loop()` in `orchestrator.py` since that is currently the primary entry
  point invoked by the ai-pr-loop workflow. The pipeline v2 `command.py` already uses `GuardsAction` which evaluates guards after snapshot construction — if v2 needs the optimization, a separate
  fast-path can be added later. This keeps the initial implementation focused and avoids touching the newer pipeline architecture unnecessarily.

- Q: Should the `trigger_label` field extraction in `_parse_pull_request_event` be extended to detect label-related `edited` events, or is label handling entirely separate (via the existing `labeled`
  action)? → A: Label handling remains entirely separate via the `labeled` action. The `edited` action on GitHub only fires for title/body/base changes. The `trigger_label` field is populated only
  from `labeled`/`unlabeled` events. No changes to label handling are needed for this feature.

## User Scenarios & Testing

### User Story 1 - Title Change Triggers Full Guard Re-evaluation (Priority: P1)

A developer or automated tool (such as GitHub Copilot) removes the `[WIP]` prefix from a PR title to signal that the PR is ready for the ai-pr-loop to process. The system must detect that the title
changed, pass through the edit-relevance guard, and then re-evaluate all subsequent guards (including the WIP-title guard) so the PR can proceed through the merge pipeline.

**Why this priority**: This is the primary motivating use case described in the source issue. Without this working correctly, removing `[WIP]` from a title would not trigger the ai-pr-loop, breaking
the core developer workflow for signaling PR readiness.

**Independent Test**: This scenario can be fully tested by simulating a `pull_request` event with `action=edited` and a changes payload indicating the title was modified. The test verifies that the
edit-relevance guard returns `(should_skip=False, reason="")` (proceed) and allows downstream guards to run. It delivers the value of ensuring title-driven state transitions are never missed.

**Acceptance Scenarios**:

1. **Given** a PR with title `[WIP] Add feature X` exists and the ai-pr-loop is configured to trigger on `edited` events, **When** a user changes the title to `Add feature X` (removing the WIP
   prefix), **Then** the orchestrator receives the event, the `EventPayload` has `title_changed=True`, the edit-relevance guard returns `(should_skip=False, reason="")` (proceed), and the WIP-title guard subsequently evaluates the new
   title and also allows the pipeline to proceed.

2. **Given** a PR with title `Add feature X` (no WIP prefix) exists, **When** a user changes the title to `[WIP] Add feature X`, **Then** the orchestrator receives the event with `title_changed=True`,
   the edit-relevance guard returns `(should_skip=False, reason="")` (proceed), and the WIP-title guard evaluates the new title and blocks with a reason indicating WIP status.

3. **Given** a PR with a title change event, **When** the `GitHubActionsProvider.parse_event()` is called with the raw GitHub webhook payload containing `changes.title.from`, **Then** the returned
   `EventPayload` has `title_changed=True` and `body_changed=False` (assuming the body did not also change).

---

### User Story 2 - Body-Only Edits Are Silently Skipped (Priority: P1)

A developer updates the PR description (body) to add context, fix typos, or update a checklist. This change has no bearing on any guard condition and should not trigger a full ai-pr-loop evaluation.
The system must detect that only the body changed and exit early with an informational log message, consuming no further CI resources.

**Why this priority**: This is equally critical to the first story because body edits are far more frequent than title changes. Without this guard, every description update would trigger an
unnecessary full pipeline run, wasting CI minutes and potentially causing rate-limit issues on busy repositories.

**Independent Test**: This scenario can be tested by simulating an `edited` event with a changes payload containing only `changes.body.from` (no title change). The test verifies that the
edit-relevance guard returns `(should_skip=True, reason="body-only edit, no guard-relevant changes")` and that no downstream guards or actions execute. The value delivered is elimination of wasted CI runs on body-only edits.

**Acceptance Scenarios**:

1. **Given** a PR exists and the ai-pr-loop triggers on `edited` events, **When** a user edits only the PR body (description) without changing the title, **Then** the `EventPayload` has
   `title_changed=False` and `body_changed=True`, the edit-relevance guard returns `(should_skip=True, reason="body-only edit, no guard-relevant changes")`, and no downstream guards or actions execute.

2. **Given** a PR exists, **When** the raw event payload from GitHub contains `changes: {body: {from: "old text"}}` but no `changes.title` key, **Then** `GitHubActionsProvider.parse_event()` returns
   an `EventPayload` with `title_changed=False` and `body_changed=True`.

3. **Given** a body-only edit event is processed, **When** the orchestrator logs the skip decision, **Then** an INFO-level log message is emitted containing the PR number and the reason for skipping,
   enabling operators to audit why the pipeline did not proceed.

---

### User Story 3 - Non-Edited Events Pass Through Unconditionally (Priority: P2)

When a PR event has an action other than `edited` (such as `opened`, `synchronize`, `labeled`, or `ready_for_review`), the edit-relevance guard must not interfere. These events do not carry title/body
change metadata and must always pass through to subsequent guards without any additional filtering.

**Why this priority**: This is essential for correctness but slightly lower priority because existing behavior already works for non-edited events. The guard must be designed to be transparent for
these cases, preserving backward compatibility.

**Independent Test**: This scenario can be tested by passing `EventPayload` instances with various `action` values (not `edited`) and verifying the edit-relevance guard unconditionally returns `(should_skip=False, reason="")`
regardless of the `title_changed` and `body_changed` field values (which default to `False`).

**Acceptance Scenarios**:

1. **Given** a PR is opened for the first time, **When** the `pull_request` event with `action=opened` is processed, **Then** the `EventPayload` has `title_changed=False` and `body_changed=False`
   (defaults), the edit-relevance guard returns `(should_skip=False, reason="")` (proceed), and all subsequent guards evaluate normally.

2. **Given** a new commit is pushed to a PR branch, **When** the `pull_request` event with `action=synchronize` is processed, **Then** the edit-relevance guard returns `(should_skip=False, reason="")` (proceed) without inspecting the
   `title_changed` or `body_changed` fields.

3. **Given** a label is added to a PR, **When** the `pull_request` event with `action=labeled` is processed, **Then** the edit-relevance guard returns `(should_skip=False, reason="")` (proceed).

---

### User Story 4 - Azure DevOps Provider Handles Edit Events (Priority: P3)

When the ai-pr-loop runs on Azure DevOps (or a future alternate provider), the provider's `parse_event()` implementation extracts title/body change information from the platform-specific webhook
payload and populates the same `title_changed` and `body_changed` fields on `EventPayload`. This ensures the edit-relevance guard works identically regardless of the CI platform.

**Why this priority**: Azure DevOps support is currently a stub implementation, so this story is lower priority. However, the data model and guard must be designed to accommodate it, and the ADO
provider should populate the fields correctly when its webhook payload contains the relevant information.

**Independent Test**: This scenario can be tested by constructing an Azure DevOps service hook payload that represents a PR update event with title changes, passing it to
`AzureDevOpsProvider.parse_event()`, and verifying the returned `EventPayload` has the correct `title_changed` and `body_changed` values.

**Acceptance Scenarios**:

1. **Given** an Azure DevOps service hook fires for a PR update that includes a title change, **When** `AzureDevOpsProvider.parse_event()` processes the payload, **Then** the returned `EventPayload`
   has `title_changed=True`.

2. **Given** an Azure DevOps service hook fires for a PR update where only the description changed, **When** `AzureDevOpsProvider.parse_event()` processes the payload, **Then** the returned
   `EventPayload` has `title_changed=False` and `body_changed=True`.

3. **Given** the ADO webhook payload does not include change metadata (e.g., older API versions), **When** `parse_event()` processes it, **Then** both `title_changed` and `body_changed` default to
   `False`, and the edit-relevance guard passes through (fail-open behavior for unknown metadata).

---

### Edge Cases

The specification must account for several boundary conditions that could arise in production. When both the title and body are changed simultaneously in a single edit event, the system must treat
this as a title change (since the title change is the guard-relevant signal) and proceed with full evaluation. When the `changes` dictionary is present in the raw payload but empty (an unusual but
possible state), the provider should set `edit_changes_known=True` while leaving `title_changed=False` and `body_changed=False`. For a non-edited action this has no effect (pass-through), and for an
`edited` action it results in skipping the pipeline run since no title change was detected.

When a CI platform's webhook does not provide change metadata at all (for example, if Azure DevOps sends a generic "updated" event
without specifying what fields changed), the system must fail open — both `title_changed` and `body_changed` remain `False`, and the
edit-relevance guard passes through rather than blocking. This ensures that incomplete metadata never causes a legitimate PR to be
ignored.

When the event action is `edited` but the raw payload contains neither title nor body changes (theoretically possible if other PR fields like
milestones or assignees were edited), the system must skip the pipeline run since no guard-relevant fields changed. The guard should log this
case at INFO level for observability.

## Requirements

### Functional Requirements

**FR-001**: The `EventPayload` dataclass MUST be extended with three new fields: `title_changed` (default `False`),
`body_changed` (default `False`), and `edit_changes_known` (default `False`).
`edit_changes_known` indicates whether the provider had reliable per-field change metadata for an `edited` event. The fields must be
immutable (consistent with the frozen dataclass pattern) and must not break any existing code that constructs `EventPayload` instances
without these fields (backward compatibility via defaults).

**FR-002**: The `GitHubActionsProvider.parse_event()` method MUST set `edit_changes_known=True` when the raw GitHub webhook payload
contains a `changes` key for an `edited` action (including when `changes` is present but empty). It MUST populate `title_changed=True`
when the payload contains a `changes.title` key and `body_changed=True` when the payload contains a `changes.body` key. When the event
action is not `edited`, or when the `changes` key is absent from the payload, `edit_changes_known` MUST remain `False` and
`title_changed`/`body_changed` MUST remain at their default value of `False`.

**FR-003**: The `AzureDevOpsProvider.parse_event()` method MUST populate the
`title_changed` and `body_changed` fields based on the Azure DevOps service hook
payload structure. When the payload includes reliable field-level change metadata,
the provider MUST set `edit_changes_known=True` and set the corresponding booleans.
For PR update/edit events, the provider MUST normalize `EventPayload.action` to
`edited` (provider-agnostic) so the edit-relevance guard can apply consistently.
When the payload does not include change metadata, `edit_changes_known` MUST
remain `False` (fail-open).

**FR-004**: A new precondition (the "edit-relevance preflight") MUST be evaluated
in the ai-pr-loop entry point (`run_ai_pr_loop()` in `orchestrator.py`) immediately after `EventPayload` is parsed and
before any provider/network calls — specifically before
`provider.get_pr_metadata(pr_number)`, lock acquisition, and
`build_pr_state_snapshot()` — and before all existing guards (the WIP-title check
is currently first). In the legacy orchestrator, the call order after this change
MUST be: (1) parse event → (2) **edit-relevance preflight** → (3)
`get_pr_metadata()` → (4) lock acquisition → (5) `build_pr_state_snapshot()` →
(6) remaining guards/actions. The preflight MUST be implemented as a standalone
function `check_edit_relevance(event: EventPayload) -> tuple[bool, str]` in
`agentic_devtools/cli/ci/guards.py`. When the event action is `edited` AND `edit_changes_known`
is `True` AND `title_changed` is `False`, the command MUST log an INFO message
and exit successfully with code 0 (`EXIT_SUCCESS`) without evaluating any downstream guards or
actions. For all other events (including `edited` events where
`edit_changes_known` is `False`), the orchestrator MUST continue with normal
processing unconditionally.

**FR-005**: When the edit-relevance preflight skips execution, it MUST provide a
human-readable reason string (suitable for logs and operator dashboards) that
identifies the event as a no-title-change edit (body-only or other non-title
edit). The reason format should be consistent with existing guard detail
strings in the codebase.

**FR-006**: The edit-relevance guard MUST emit an INFO-level log message when it
skips execution, including the PR number and the specific reason (e.g.,
"PR #123: skipping edited event — no title change detected"). This log message
enables operators to distinguish intentional skips from unexpected guard failures
during incident investigation.

**FR-007**: The workflow YAML file(s) that define the ai-pr-loop trigger MUST
include `edited` in the `pull_request` event types list. No additional `if:`
conditions related to title/body changes shall be added to the YAML — all
filtering logic resides in the Python orchestrator. This keeps the YAML minimal
and the logic testable.

**FR-008**: When both `title_changed` and `body_changed` are `True` (simultaneous
edit of both fields), the edit-relevance guard MUST return `(should_skip=False, reason="")` (proceed) because the
title change is guard-relevant. The presence of a body change alongside a title
change does not alter the decision.

**FR-009**: Documentation and/or examples MUST be updated to clarify that PR
`edited` event filtering (title/body change relevance) is implemented in the
Python orchestrator (edit-relevance guard), not in workflow-level YAML `if:`
conditions.

### Non-Functional Requirements

**NFR-001**: The edit-relevance decision MUST complete in under 1 millisecond for
any input, as it performs only in-memory inspection of `EventPayload` fields with
no I/O. When it decides to skip (body-only/no-title-change edit), the ai-pr-loop
command MUST exit before performing any network calls (e.g., fetching PR metadata
or building a PR state snapshot).

**NFR-002**: The implementation MUST maintain full backward compatibility with
existing `EventPayload` construction patterns. Any code that creates
`EventPayload(pr_number=1, head_branch="main", ...)` without specifying
`title_changed` or `body_changed` MUST continue to work without modification,
with both new fields defaulting to `False`.

**NFR-003**: All new guard logic MUST be covered by unit tests following the
repository's 1:1:1 test structure policy. Test files must be placed under
`tests/unit/` with paths mirroring the source structure, and each test file must
target a single symbol (function or class). Specifically:

- `tests/unit/cli/ci/guards/test_check_edit_relevance.py` for the guard function
- `tests/unit/cli/ci/models/test_eventpayload.py` (extend existing) for the new fields
- `tests/unit/cli/ci/github_provider/test_parse_event.py` (extend existing) for GitHub provider changes

**NFR-004**: Log messages emitted by the edit-relevance guard MUST use the
standard Python `logging` module at INFO level and follow the existing log
message formatting conventions used by other guards in `guards.py`. The messages
must not contain sensitive information (no raw payload dumps).

### Key Entities

**EventPayload** (extended): The immutable dataclass representing a normalized CI
event. It gains three new fields to describe `edited` events: `title_changed`
(default `False`), `body_changed` (default `False`), and `edit_changes_known`
(default `False`) to indicate whether the provider had reliable per-field change
metadata. This entity is the single point of truth consumed by all guards and
downstream pipeline actions.

**Edit-Relevance Guard** (`check_edit_relevance`): A standalone function in
`agentic_devtools/cli/ci/guards.py` that inspects the `action`,
`edit_changes_known`, and `title_changed` fields of an `EventPayload` to
determine whether the event warrants full pipeline evaluation. Returns
`(should_skip: bool, reason: str)`. It is purely in-memory (no I/O); when it
decides to skip, the orchestrator logs the reason and exits 0 without running
any downstream guards or actions.

## Success Criteria

### Measurable Outcomes

- **SC-001**: The ai-pr-loop MUST trigger and complete a full guard evaluation on
  100% of PR title change events across both GitHub Actions and Azure DevOps
  providers, verified by integration tests that simulate title-change payloads
  and assert the pipeline proceeds past the edit-relevance guard.

- **SC-002**: The ai-pr-loop MUST skip execution (exit at the edit-relevance
  guard) on 100% of body-only edit events, verified by integration tests that
  simulate body-change payloads and assert no downstream guards or actions
  execute. In production, this is expected to eliminate at least 80% of
  unnecessary `edited`-event pipeline runs (based on the observation that body
  edits outnumber title edits approximately 4:1).

- **SC-003**: All new code (the `EventPayload` fields
  `title_changed`, `body_changed`, `edit_changes_known`, provider
  `parse_event()` changes, and the edit-relevance guard) MUST achieve
  100% line and branch coverage in unit tests, consistent with the
  repository's existing coverage requirements enforced by CI.

- **SC-004**: The edit-relevance guard MUST be the first guard evaluated in the
  `GuardsAction` sequence, verified by a unit test that asserts guard ordering
  and by an integration test confirming that a body-only edit does not trigger
  evaluation of any subsequent guard (WIP check, fork check, etc.).

- **SC-005**: Zero regressions in existing guard behavior, verified by the full
  existing test suite (`tests/unit/cli/ci/`) passing without modification. The
  new guard is purely additive and MUST NOT alter the semantics of any existing
  guard for non-edited events.

- **SC-006**: The `EventPayload` extension MUST maintain backward compatibility,
  verified by confirming that all existing tests that construct `EventPayload`
  instances continue to pass without adding the new fields to their constructor
  calls.

---
*Generated by Copilot SDK (claude-opus-4.6)*
