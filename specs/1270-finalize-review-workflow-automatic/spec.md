# Feature Specification: Finalize review workflow — automatic PR comment repair/finalization step

**Feature Branch**: `speckit/1270/phase-1-specify`
**Created**: 2026-05-03
**Status**: Draft
**Input**: Add automatic agentic-devtools prompt-based PR comment repair/finalization step to agdt-initiate-pull-request-review-workflow
**Source Issue**: #1270

## Summary

Add an automatic finalization step to `agdt-initiate-pull-request-review-workflow` so that, during the existing
`completion` step, the workflow repairs and finalizes PR review comments that were generated through the
agentic-devtools prompt-based review flow. The goal is to converge review thread content into a correct final state
without introducing a new workflow state or requiring a separate manual repair pass.

This spec assumes finalization integrates into the existing `completion` step (no new workflow state), reuses
existing session-closing and cascade internals where they already provide the required behavior, and leverages
the existing thread-classification and PAT-identity-resolution capabilities for authorship scoping.

## Problem Statement

The `agdt-initiate-pull-request-review-workflow` generates prompt-based PR review comments during its review passes.
When the workflow reaches the `completion` step, these comments may be in an intermediate or inconsistent state —
partial marker content, stale summaries, or formatting artifacts from the iterative review process. Currently there
is no automated repair/finalization pass, forcing reviewers to either accept imperfect comment state or manually
re-edit threads after completion. This creates friction, reduces trust in the review output, and leaves review
threads in a non-converged state that downstream consumers cannot reliably parse.

A deterministic finalization pass embedded in the existing completion step would ensure prompt-based review comments
converge to their expected final form without manual intervention or a new workflow phase.

## Scope

In scope:

- Automatic repair/finalization of prompt-based PR review comments created by the review workflow
- Thread classification and authorship scoping so only eligible comments are modified
- Batch-first repair via a single batch-review submission (single final cascade) followed by targeted
  per-comment repair where needed
- Verification/retry behavior to confirm state convergence
- Reporting of actions taken, skipped items, and non-blocking failures

Out of scope:

- Introducing a new workflow step or persisted workflow state machine node
- Editing comments not attributable to the current PAT identity
- Changing the semantics of manual review comments authored outside the prompt-based workflow
- Replacing existing cascade/finalization internals rather than orchestrating them

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Automatic finalization after review completion (Priority: P1)

As a reviewer running `agdt-initiate-pull-request-review-workflow`, I want the workflow to automatically finalize
prompt-based PR review comments during completion so that the review ends in a consistent and polished state
without a manual clean-up step.

**Why this priority**: This is the core feature — without automatic finalization, the entire spec has no value.
Every other story depends on this orchestration being in place.

**Independent Test**: Can be fully tested by running the workflow to completion on a PR with prompt-based review
comments and verifying that eligible comments are repaired/finalized without manual intervention.

**Acceptance Scenarios**:

1. **Given** the workflow reaches the existing `completion` step and prompt-based review comments exist,
   **When** the finalization logic runs, **Then** eligible comments are repaired or finalized automatically.
2. **Given** the workflow reaches completion and no eligible prompt-based comments exist,
   **When** finalization runs, **Then** the workflow completes successfully and reports that no action was required.
3. **Given** existing completion behavior (session closing, cascade updates), **When** finalization is added,
   **Then** all prior completion behavior remains intact apart from the added repair/finalization pass.

---

### User Story 2 — Safe authorship scoping (Priority: P1)

As a reviewer using a PAT-backed identity, I want the workflow to modify only comments attributable to my current
authenticated identity so that it never repairs or overwrites someone else's review content.

**Why this priority**: Modifying another user's comments would be a correctness and trust violation. This safety
boundary must be enforced before any mutations occur.

**Independent Test**: Can be tested by running finalization against a PR with mixed-author comments and verifying
that only comments matching the authenticated PAT identity are mutated, while others are skipped and reported.

**Acceptance Scenarios**:

1. **Given** the workflow resolves the current PAT identity successfully, **When** finalization encounters a
   comment authored by the same identity, **Then** it is considered eligible for repair.
2. **Given** the workflow resolves the current PAT identity, **When** finalization encounters a comment authored
   by a different user, **Then** the comment is skipped and the skip reason is included in reporting.
3. **Given** PAT identity resolution fails or returns insufficient data, **When** finalization attempts to run,
   **Then** no comments are mutated and the failure is reported without corrupting review state.

---

### User Story 3 — Batch-first repair strategy (Priority: P2)

As a maintainer, I want the workflow to drive the bulk repair through a single batch-review submission
(which performs one final overall cascade after the batch) before falling back to targeted per-comment fixes,
so that normal cases are efficient and avoid reintroducing multiple-cascade behavior.

**Why this priority**: Efficiency matters for large PRs with many review threads. A batch-first approach
reduces API calls in the common case while the fallback ensures completeness.

**Independent Test**: Can be tested by running finalization on a PR where some comments need repair. Verify that
the batch pass is attempted first, and only remaining non-converged comments are handled individually.

**Acceptance Scenarios**:

1. **Given** multiple eligible comments that all converge via the batch-first strategy, **When** finalization
   runs, **Then** no targeted per-comment fallback is triggered and the report indicates batch-only success.
2. **Given** the batch-first strategy leaves some comments non-converged, **When** finalization detects
   incomplete convergence, **Then** targeted repair runs only for the remaining non-converged comments.
3. **Given** targeted repair is invoked, **When** it processes a comment, **Then** it only touches comments
   still identified as non-converged after the batch pass.

---

### User Story 4 — Verified convergence (Priority: P2)

As a maintainer, I want finalization to verify the resulting thread state after repair attempts so that the
workflow can distinguish success, partial success, and non-blocking failure based on actual repository state
rather than optimistic assumptions.

**Why this priority**: Without verification, the workflow cannot reliably report whether finalization succeeded.
Accurate status reporting is necessary for trust and for downstream automation.

**Independent Test**: Can be tested by mocking API responses to simulate partial convergence and verifying that
the workflow correctly classifies the outcome as partial success rather than full success.

**Acceptance Scenarios**:

1. **Given** all eligible comments converge after repair, **When** verification re-reads thread state,
   **Then** finalization reports full success.
2. **Given** some eligible comments do not converge after the initial pass, **When** the retry strategy executes
   within timeout limits, **Then** the workflow makes additional attempts before declaring partial success.
3. **Given** convergence still fails after retries, **When** the verification window expires, **Then** the
   workflow reports non-blocking failure with details of which comments did not converge.

---

### User Story 5 — Actionable reporting (Priority: P3)

As an operator or future debugging reviewer, I want the workflow to emit a useful report of what it changed,
skipped, and failed to verify so that I can understand the finalization outcome without reading raw implementation
details.

**Why this priority**: Reporting is important for auditability and debugging but does not block core functionality.
The workflow can succeed without perfect reporting.

**Independent Test**: Can be tested by running finalization in both normal and dry-run modes and verifying the
report includes counts for repaired, skipped, unchanged, and failed items with clear status distinctions.

**Acceptance Scenarios**:

1. **Given** finalization completes (full or partial success), **When** the report is emitted, **Then** it
   includes counts and details for repaired, finalized, skipped, unchanged, and failed items.
2. **Given** dry-run mode is active, **When** finalization runs, **Then** no comment mutations occur but the
   report shows what would have been changed.
3. **Given** a no-op scenario (all comments already correct), **When** the report is produced, **Then** it
   clearly distinguishes no-op success from degraded success.

---

### Edge Cases

- What happens when no eligible prompt-based review comments exist? → Finalization completes successfully,
  reports no action required.
- How does the system handle a comment whose content already exactly matches the expected final state? → It is
  left unchanged and counted as "already finalized" in reporting.
- What happens when PAT identity resolution times out? → No mutations occur; failure is reported as non-blocking.
- What if the batch-first strategy partially succeeds but leaves one comment in an unexpected intermediate
  state? → Targeted fallback attempts repair; if that also fails, partial success is reported.
- What happens when the API rate limit is hit during comment patching? → The system respects retry-after headers
  and reports any comments that could not be patched within the timeout window.
- What happens when `review-state.json` is missing or corrupt at completion time? → Finalization reports no
  eligible comments (no-op success) and does not block the completion step. The system does not attempt to
  reconstruct review state from API data alone.
- What if a comment's marker is valid but the thread has been deleted or is inaccessible? → The comment is
  counted as a non-blocking failure in reporting and does not prevent other comments from being finalized.

## Requirements *(mandatory)*

### Functional Requirements

#### Finalization orchestration

- **FR-001**: The system **MUST** execute the automatic prompt-based PR comment repair/finalization pass during
  the existing `completion` step of `agdt-initiate-pull-request-review-workflow`.
- **FR-002**: The system **MUST NOT** introduce a new persisted workflow state or require a new user-visible
  workflow phase to perform finalization.
- **FR-003**: The implementation **MUST** reuse existing session-closing, cascade-update, and comment-patching
  internals where those internals already provide the required behavior, rather than duplicating equivalent
  orchestration logic. Specifically, the batch-first pass **MUST** reuse the existing `submit_reviews()`
  function (or its underlying parallel file-processing and single-cascade logic) as the entry point for
  driving file-summary convergence. For activity-log entry finalization, `_complete_active_session()` is the
  primary entry point for completing the current session (which internally calls
  `_update_activity_log_comment_status()`), while `_update_activity_log_comment_status()` **MAY** be invoked
  directly only for targeted fallback repairs of individual activity-log entries that were not covered by
  the session-completion path.

#### Thread/comment eligibility and classification

- **FR-004**: The system **MUST** classify which PR review threads/comments are part of the agentic-devtools
  prompt-based review flow and therefore eligible for repair/finalization.
  Eligible comment types include: file summary threads (marker type `file-summary`), the overall PR summary
  thread (marker type `overall-summary`), and review-session reply comments within the activity-log thread
  (marker type `activity-log-entry`). Classification **MUST** use the existing `classify_agdt_threads()` and
  `parse_marker()` functions from `agentic_devtools.cli.azure_devops.marker` as the primary mechanism,
  consistent with FR-012.
- **FR-005**: The system **MUST** limit repair/finalization attempts to comments that are both classified as
  eligible prompt-based comments and attributable to the current authenticated PAT identity.
- **FR-006**: The system **MUST** skip comments that are unclassified, ambiguously classified, or classified as
  outside the prompt-based review flow.
- **FR-007**: The system **MUST** skip comments authored by a different identity, and the skip reason **MUST** be
  represented in the finalization reporting.
- **FR-020**: The system **MUST** classify review-session reply comments (bearing the `activity-log-entry`
  marker) as eligible for finalization and **MUST** rewrite the reply belonging to the current review session
  and commit into its completed form (e.g., replacing intermediate status strings like `New Review` or
  `Resuming` with the terminal session-complete content rendered by `_update_activity_log_comment_status` with
  `status_emoji="✅"` and `status_text="Completed"`). The system **MUST NOT** finalize activity-log
  entries belonging to other review sessions or commits, as those represent independent review cycles with
  their own audit trails. Session/commit scoping **MUST** be determined by matching the session ID
  (from the `*Session ID:*` line) embedded in the activity-log entry's body content against the current
  review session in `review-state.json`. Additionally, the commit hash (from the `*Commit:*` line) **MAY**
  be used as a secondary scoping signal via prefix comparison (the rendered short hash is a prefix of the
  full `commitHash` stored in `review-state.json`).

#### Identity resolution

- **FR-008**: The system **MUST** resolve the current PAT-backed identity before mutating repairable comments.
  Identity is resolved by calling the Azure DevOps Connection Data API (`/_apis/connectionData`) using the
  configured PAT, which returns the authenticated user's `id` (required for authorship checks). The display
  name field (e.g., `providerDisplayName` or `customDisplayName`) is optional and implementation-defined.
  The resolved identity is compared against each comment's `author.id` field (GUID equality).
- **FR-009**: If PAT identity resolution fails or returns insufficient data, the system **MUST NOT** mutate any
  comments whose authorship cannot be confidently established.

#### Repair strategy and matching behavior

- **FR-010**: The system **MUST** drive the bulk repair/finalization pass through a single batch-review
  submission (producing one final overall cascade) rather than issuing repeated single-file
  approve/request-changes calls that would reintroduce multiple-cascade behavior. The batch pass **MUST**
  ensure that no per-file cascade is triggered during individual file processing, and that at most one
  `execute_cascade()` call is performed at the end of the batch (skipped when no file operations succeeded,
  consistent with existing `submit_reviews()` behavior). The implementation **MAY** achieve this
  through any suitable in-process entry point (e.g., the internal parallel file-processing path of
  `submit_reviews()`) consistent with CLAR-003 (synchronous completion execution path), as long as the
  single-cascade invariant is preserved.
- **FR-021**: The batch pass **MUST** preserve each file's existing review outcome (approved vs.
  needs-work) and associated summary/suggestion content. The system **MUST NOT** alter a file's verdict
  solely to force terminal comment content; each file's final posted comment **MUST** reflect the actual
  review decision and reasoning that was originally recorded for that file.
- **FR-011**: If the batch pass does not produce full expected convergence, the system **MUST** fall back
  to targeted repair for only the remaining non-converged eligible comments. The targeted fallback
  **MUST** produce comment content consistent with the authoritative review state rather than writing
  ad-hoc comment bodies directly, preventing drift between the persisted review decisions and the
  posted comment content visible to users. Targeted repair uses direct Azure DevOps PATCH
  `threads/{threadId}/comments/{commentId}` API calls with content rendered from `render_file_summary()`
  or `render_overall_summary()` against the authoritative `review-state.json` data, and
  `_update_activity_log_comment_status()` from `review_scaffold.py` for activity-log entries.
  Because the renderers return body-only content (without the leading `<!-- agdt-review:v1 ... -->` marker
  line), targeted repair **MUST** prepend the appropriate marker (via `build_marker(...)`) before PATCHing
  the comment, preserving the marker metadata required for future classification.
- **FR-012**: The system **MUST** use the existing structured marker-parsing mechanisms (specifically
  `marker.py`'s public API — `parse_marker()`, `has_agdt_marker()`, and `classify_agdt_threads()` —
  rather than fragile content heuristics) to identify and scope candidate comments for
  repair/finalization.
  Marker parsing alone **MUST NOT** be treated as sufficient to determine whether a comment's current
  body is already in its correct terminal form, because marker metadata does not encode review-status
  text, placeholder narrative content, or model-progress rows. The system **MUST** determine whether a
  comment is already correct, still repairable, or still needs patching by comparing the current
  comment body against the expected terminal rendering for that comment type (produced by
  `render_file_summary()` and `render_overall_summary()` from `review_templates.py`). Because Azure DevOps
  comment content includes the AGDT marker prefix line (prepended at post/patch time via `build_marker()`)
  while the renderers produce body-only content, convergence comparison **MUST** normalize by stripping the
  leading marker line from the observed comment content before comparing against the expected rendering.
  The classification logic **SHOULD** leverage structured AGDT markers for safe candidate matching and use
  rendered-content comparison (after marker-line normalization) for convergence validation, rather than
  requiring brittle ad-hoc heuristics.
- **FR-013**: The system **SHOULD** avoid patching comments whose current content already exactly matches the
  expected final content.
- **FR-014**: The system **MAY** leave already-correct comments unchanged while still counting them in reporting
  as unchanged or already finalized.

#### Verification and convergence

- **FR-015**: After each repair/finalization pass, the system **MUST** verify observed state convergence by
  re-reading the relevant thread/comment content from the Azure DevOps API (not from local cache or
  optimistic state) and comparing the fetched content against the expected terminal rendering. This ensures
  verification reflects the actual repository state rather than optimistic local assumptions.
- **FR-022**: Convergence for file summary and overall summary comments is defined as reaching their terminal
  content state — only the final `approved` or `needs-work` renderings are valid terminal content. Placeholder
  or intermediate strings (e.g., `Awaiting review...`, in-progress status sections, partial marker content)
  **MUST** be removed or replaced with the correct terminal rendering for the comment to be considered converged.
  Convergence additionally requires that:
  - The `### Model Review Progress` table (if present) contains **only** terminal model verdicts
    (e.g., `✅ Approved`, `⚠️ Needs Work`). Rows with intermediate states such as `⏳ Awaiting Review`
    or `🔃 In Progress` **MUST** be resolved to their terminal verdict or removed before the comment
    is considered converged.
  - The overall PR summary thread **MUST NOT** contain stale file links from earlier review cycles.
    Files that are no longer part of the current review scope (e.g., removed from the PR diff or
    classified as out-of-branch/skipped during prompt generation) **MUST** be pruned from the summary
    to reflect only the files in the active `review-state.json` file entries for the current commit.
- **FR-023**: Convergence for `activity-log-entry` comments is defined as the current session's
  review-session reply reaching its terminal completed state as produced by the existing renderer
  (`_format_activity_log_entry` with `status_emoji="✅"` and `status_text="Completed"`).
  Intermediate status strings (e.g., `New Review`, `Resuming`) **MUST** be replaced with the terminal
  session-complete content. The comment is considered converged only when its full body matches the
  canonical completed output — partial content or alternate prose that omits required elements
  **MUST NOT** be considered converged.
- **FR-016**: The system **MUST** treat finalization as successful only when all eligible targeted comments
  converge to the expected final state within the allowed execution window.
- **FR-017**: If some eligible comments do not converge, the system **MUST** report partial success or
  non-blocking failure rather than silently reporting full success.

#### Reporting

- **FR-018**: The system **MUST** produce a finalization report that includes, at minimum, which eligible
  comments were repaired/finalized, which were skipped and why, which were unchanged, and whether convergence
  was achieved fully, partially, or not at all. The report **MUST** be emitted to stdout (for interactive
  consumption) and also persisted to the workflow state directory as
  `finalization-report-{commit_hash_short}.json` for automated downstream consumption.

#### Resilience

- **FR-019**: When `review-state.json` is missing or corrupt at completion time, the finalization pass
  **MUST** treat this as a no-op success: report "no eligible comments (review state unavailable)" and
  allow the completion step to proceed normally without blocking. The system **MUST NOT** attempt to
  reconstruct review state from API data alone. This is consistent with NFR-002 (non-blocking failures).

### Non-Functional Requirements

- **NFR-001**: The finalization process **MUST** complete within 60 seconds in the normal bounded execution path,
  including verification and any permitted retry/fallback behavior. The retry model uses bounded global retry
  rounds (not independent per-comment timers): after the initial batch pass, up to 2 additional retry rounds
  are performed across all remaining non-converged comments, with a 5-second delay between rounds. Each round
  targets only comments that have not yet converged. This caps the retry overhead at a fixed 10 seconds of
  backoff regardless of the number of non-converged comments, keeping the worst case well within the 60-second
  budget.
- **NFR-002**: Failures in the finalization process **MUST** be non-blocking to the overall completion step
  unless an existing higher-level workflow failure condition already requires termination.
- **NFR-003**: The implementation **MUST** support dry-run behavior such that no comment mutations occur while
  still producing a meaningful preview report of intended actions. Dry-run is activated when the `dry_run`
  state key is truthy, consistent with the existing `agdt-set dry_run true` pattern and `is_dry_run()` utility.
- **NFR-004**: The implementation **MUST** be idempotent: rerunning the same finalization logic against an
  already-converged state must not introduce duplicate mutations or incorrect drift.
- **NFR-005**: The implementation **SHOULD** minimize unnecessary API calls by skipping already-correct comments
  and by preferring batch-first convergence where possible.
- **NFR-006**: The implementation **SHOULD** emit concise, diagnosable reporting suitable for both interactive
  runs and automated workflow logs.

## Success Criteria

1. When finalization runs during the completion step of a PR with prompt-based review comments, all eligible
   comments converge to their expected final state without manual intervention.
2. Comments authored by other users are never mutated — verified by running against a PR with mixed-author
   review threads.
3. For a PR where all eligible comments are repairable during the normal finalization pass, the workflow
   completes with all eligible comments in their expected final state and the report indicates full success.
4. Dry-run mode produces an accurate preview of intended actions without mutating any comments.
5. The finalization report clearly distinguishes full success, partial success, no-op, and failure outcomes.
6. Rerunning finalization on an already-converged PR produces no duplicate mutations and reports no-op success.
7. The entire finalization pass completes within 60 seconds for a PR with up to 50 prompt-based review comments.

## Clarifications

- **CLAR-001 — Narrative generation method:** The finalization step repairs/finalizes existing prompt-based
  review comments and reporting narrative using deterministic workflow logic and existing internals; it does not
  require introducing a new LLM generation phase inside completion.
- **CLAR-002 — Workflow step placement:** The feature is intentionally embedded in the existing `completion`
  step, and no additional workflow state, checkpoint, or user action is introduced.
- **CLAR-003 — Completion-step behavior:** Finalization occurs during the workflow's `completion` step and
  **MUST** preserve the existing non-blocking error-handling and reporting expectations, without requiring a
  separate user-visible repair phase.

### Session 2026-05-04

- Q: How does the finalization pass invoke the batch-review submission synchronously within the completion step, given that `submit_reviews()` is designed as a CLI entry point that reads from state? →
  A: The finalization orchestrator calls `submit_reviews()` (or its underlying internal logic) as a direct in-process Python function call within the completion step. It pre-populates the required
  state keys (`batch_reviews.items`, `pull_request_id`) before invocation and reads results from state/review-state afterward. This is consistent with CLAR-003 and avoids spawning a subprocess or
  background task for an operation that must complete synchronously within the 60-second window.
  Because `submit_reviews()` calls `sys.exit(1)` on validation errors or file-review failures, the
  finalization orchestrator **MUST** invoke the underlying non-exiting logic path (e.g., the internal
  file-processing and cascade functions) rather than the top-level CLI entry point, or alternatively
  catch `SystemExit` and translate it into a non-blocking failure report. This ensures the completion
  step is never aborted by an exit call, consistent with NFR-002's non-blocking requirement.
- Q: What is the expected retry strategy when targeted per-comment repair fails — exponential backoff, fixed delay, or bounded retries? → A: Bounded global retry
  rounds with fixed backoff: after the initial batch pass, up to 2 additional retry rounds are performed across all remaining non-converged comments, with a 5-second delay between rounds. Each round
  targets only comments that have not yet converged. This caps retry overhead at a fixed 10 seconds of backoff regardless of comment count, keeping the worst case well within the 60-second NFR-001
  budget while allowing transient API errors to resolve. Applied to NFR-001.
- Q: When `review-state.json` is missing or corrupt at completion time (e.g., interrupted workflow, manual deletion), should finalization fail loudly or treat it as a no-op? → A: Treat as a no-op:
  report "no eligible comments (review state unavailable)" and allow the completion step to proceed normally. This is consistent with NFR-002 (non-blocking failures) and matches the existing
  `_complete_active_session()` pattern which silently returns on `FileNotFoundError`. Added to Edge Cases.
- Q: Should the finalization report be persisted to disk (e.g., as a JSON file in the state directory) or only emitted to stdout? → A: Both — emit a human-readable summary to stdout for interactive
  use, and persist a structured JSON report to `finalization-report-{commit_hash_short}.json` in the workflow state directory for automated consumption and auditability. Applied to FR-018.
- Q: How does identity comparison work — is it `author.id` equality, `author.displayName` matching, or something else? → A: Identity comparison uses `author.id` (GUID) equality, which is the stable
  unique identifier in Azure DevOps. Display names are not reliable for identity comparison due to potential duplicates and changes. The PAT identity's `id` is obtained from the Connection Data API
  (`/_apis/connectionData`). Applied to FR-008.

## Notes for subsequent phases

- Thread classification and authorship scoping are hard safety boundaries that later phases must not relax.
- The finalization report must distinguish between: no eligible comments found, eligible comments already
  correct, eligible comments repaired successfully, eligible comments partially converged, and eligible
  comments that failed to converge within the allowed execution window.
- The retry strategy (2 additional attempts, 5-second fixed backoff) may need tuning in subsequent phases based
  on observed API latency patterns for large PRs. The 60-second budget provides headroom for adjustment.
- Finalization execution ordering (after `_complete_active_session`, before workflow-state cleanup) is a
  sequencing contract that subsequent phases must preserve if they add additional completion-step logic.

---
*Generated by Copilot SDK (claude-opus-4.6)*
