# Spec: Remove active session precondition from resolve_threads action

**Feature Branch**: `speckit/1569/phase-1-specify`  
**Created**: 2026-05-26  
**Status**: Draft  
**Input**: GitHub Issue #1569  
**Source Issue**: #1569 (<https://github.com/ayaiayorg/agentic-devtools/issues/1569>)  

---

## Problem Statement

The `ResolveThreadsAction` in `agentic_devtools/cli/ci/pipeline/actions/resolve_threads.py`
currently has `no_active_session` as its first precondition (lines 33–41 of `evaluate()`).
When a Copilot coding session is detected as active, the action returns
`ActionDecision.SKIP` immediately with the message "Copilot coding session is active",
preventing any thread-resolution work from taking place.

This precondition is overly conservative. Thread resolution evaluates whether review
feedback has already been addressed in the code by comparing comment commit SHAs against
the current `HEAD` SHA (the `r.commit_sha != snapshot.head_sha` filter inside `execute()`).
That filter is the correct gate: if no new commit exists since the review, there is nothing
to resolve. The question of whether a Copilot coding session is currently active has no
bearing on whether prior review threads can be evaluated and closed — the session may well
have produced the very commit that addresses those threads.

By keeping the `no_active_session` guard, the loop introduces an artificial delay: threads
can only be resolved after the session terminates, even though the commit that addresses
them exists. Removing the guard allows the loop to resolve threads as soon as the relevant
preconditions (CI passing, no pending review on HEAD, unresolved threads exist) are
satisfied — regardless of whether a coding session is running concurrently.

The companion spec `specs/1559-refactor-loop-into-idempotent/spec.md` must also be
updated: FR-005 in that spec currently states that thread resolution MUST NOT execute
when a Copilot coding session is active. This constraint was accurate before the current
change but is incorrect afterward. The other two actions governed by that FR (squash and
dispatch-repair) still require the `no_active_session` guard, so only the
resolve-threads portion of FR-005 must be removed.

---

## Clarifications

### Session 2026-05-26

- Q: After removing the `no_active_session` block (lines 33–41), should the
  precondition evaluation order remain CI → pending review → unresolved threads,
  or should it change?
  → A: The order MUST remain CI → pending review → unresolved threads. This is
  the existing order of the remaining checks (lines 43–73) and preserves
  deterministic skip-reason reporting. No reordering is required.

- Q: When updating spec 1559 FR-005, should the requirement be split into two
  separate FR entries (one for thread-resolution, one for squash/dispatch-repair),
  or should FR-005 be reworded in place to exclude resolve-threads?
  → A: FR-005 should be reworded in place to exclude resolve-threads from the
  session gate, rather than split into two entries. Splitting would renumber
  downstream requirements and break cross-references. The updated text should
  state that only squash and dispatch-repair MUST NOT execute when a session is
  active, and that thread resolution is not session-gated.

- Q: Should spec 1559 User Story 2 acceptance scenario 1 (line 93–94, which
  lists resolve-threads among actions skipped when session is active) also be
  updated, or only acceptance scenario 2 of User Story 3?
  → A: Both must be updated. User Story 2 acceptance scenario 1 (line 93–94)
  must remove "resolve-threads" from the list of actions skipped when a session
  is active, leaving only dispatch-repair and squash. User Story 3 acceptance
  scenario 2 (line 121) must be removed or rewritten to reflect that thread
  resolution proceeds regardless of session state. FR-007 in this spec is
  updated to cover both locations.

- Q: The `execute()` method returns `ActionDecision.SKIP` with reason
  "No prior Copilot reviews found (race condition)" when `prior_reviews` is
  empty. Should the `preconditions` dict be populated in this `execute()`-level
  SKIP result?
  → A: No change required. The existing `execute()` SKIP path does not populate
  `preconditions` (it only sets `name`, `decision`, and `details`). This is
  correct behaviour because `preconditions` is an `evaluate()`-level concept —
  `execute()` has already passed evaluation. This implicit gate is preserved
  unchanged per FR-005 of this spec.

- Q: Does 100% line coverage (NFR-003) include the `execute()` method's
  "No prior Copilot reviews found (race condition)" branch, or only the
  `evaluate()` method?
  → A: 100% line coverage applies to the entire `resolve_threads.py` file,
  including all branches in both `evaluate()` and `execute()`. The
  "race condition" branch in `execute()` must be covered by a test that
  constructs a snapshot with `unresolved_threads > 0` (to pass `evaluate()`)
  but with no matching prior reviews in `snapshot.reviews`.

---

## User Scenarios & Testing

### User Story 1 — Thread Resolution Proceeds When Session Is Active (Priority: P1)

As the ai-pr-loop automation, I want unresolved Copilot review threads to be evaluated
and resolved even while a Copilot coding session is active, so that feedback from prior
reviews is addressed as soon as the relevant commit exists on the branch without waiting
for the session to terminate.

**Why this priority**: This is the core behaviour change. Without removing the session
guard, the remaining user stories have no value — everything else (spec updates, tests)
is in service of this fix.

**Independent Test**: Can be fully tested by simulating a PR snapshot with
`active_session=True`, `ci_status="passing"`, `copilot_review_pending=False`, and
`unresolved_threads > 0`, then calling `ResolveThreadsAction.evaluate()` and asserting
the result is `ActionDecision.EXECUTE` (not `SKIP`).

**Acceptance Scenarios**:

1. **Given** a PR where `active_session=True`, CI is passing, no Copilot review is
   pending on HEAD, and 3 unresolved threads exist from a prior commit,
   **When** `ResolveThreadsAction.evaluate()` is called,
   **Then** it MUST return `ActionDecision.EXECUTE` with `"has_unresolved_threads": True`
   in `preconditions` and MUST NOT contain `"no_active_session"` in `preconditions`.

2. **Given** the same PR state where `active_session=True` and preconditions are met,
   **When** `ResolveThreadsAction.execute()` is called,
   **Then** it MUST delegate to `provider.finalize_post_repair()` for each prior Copilot
   review and update `derived.unresolved_threads` with the post-resolution count.

3. **Given** a PR where `active_session=False` and all other preconditions are met,
   **When** `ResolveThreadsAction.evaluate()` is called,
   **Then** it MUST still return `ActionDecision.EXECUTE` (behaviour is unchanged when
   no session is active — removing the guard must not regress the non-session path).

---

### User Story 2 — Remaining Preconditions Are Still Enforced (Priority: P1)

As the ai-pr-loop automation, I want thread resolution to continue to be gated on CI
passing, no pending Copilot review on HEAD, and at least one unresolved thread existing,
so that threads are only resolved when resolution is meaningful and safe.

**Why this priority**: Equal priority to User Story 1 because partial removal of guards
would create unsafe states — CI must pass before finalization, and a pending review means
new feedback may be incoming.

**Independent Test**: Can be tested by constructing three independent snapshots — one
with `ci_status="failing"`, one with `copilot_review_pending=True`, and one with
`unresolved_threads=0` — and asserting `ActionDecision.SKIP` for each.

**Acceptance Scenarios**:

1. **Given** a PR where `active_session=True` AND `ci_status="failing"`,
   **When** `ResolveThreadsAction.evaluate()` is called,
   **Then** it MUST return `ActionDecision.SKIP` with `"ci_passing": False` in
   `preconditions` and details indicating CI is failing.

2. **Given** a PR where `active_session=True` AND `copilot_review_pending=True`
   AND CI is passing,
   **When** `ResolveThreadsAction.evaluate()` is called,
   **Then** it MUST return `ActionDecision.SKIP` with `"no_pending_review": False` in
   `preconditions` and details indicating a Copilot review is pending.

3. **Given** a PR where all session/CI/review preconditions pass BUT
   `unresolved_threads=0`,
   **When** `ResolveThreadsAction.evaluate()` is called,
   **Then** it MUST return `ActionDecision.SKIP` with `"has_unresolved_threads": False`
   in `preconditions` and details indicating no unresolved threads.

---

### User Story 3 — FR-005 in Spec 1559 Updated to Reflect New Precondition Set (Priority: P2)

As a developer reading the companion spec
`specs/1559-refactor-loop-into-idempotent/spec.md`, I want FR-005 to accurately describe
the preconditions for thread resolution (without the session gate) and still accurately
describe the session requirement for squash and dispatch-repair, so that the spec remains
a trustworthy reference.

**Why this priority**: Spec consistency is important for long-term maintainability and
for automated tools (such as the SpecKit E.2 classifier) that derive task metadata from
FR descriptions, but it is secondary to the code change itself.

**Independent Test**: Can be verified independently by reading the updated FR-005 text
and confirming that (a) `resolve_threads` is no longer listed as session-gated and
(b) `squash` and `dispatch-repair` are still listed as session-gated. No code execution
is required.

**Acceptance Scenarios**:

1. **Given** `specs/1559-refactor-loop-into-idempotent/spec.md` after the update,
   **When** FR-005 is read,
   **Then** it MUST NOT contain any statement that resolve-threads is skipped when a
   Copilot coding session is active.

2. **Given** the updated FR-005 in spec 1559,
   **When** it is read,
   **Then** it MUST still state that squash (action 6) and dispatch-repair MUST NOT
   execute when a Copilot coding session is active, preserving the requirement for those
   actions unchanged.

3. **Given** FR-005 references in User Story 2 acceptance scenario 1 (line 93–94, which
   lists resolve-threads among skipped actions) and User Story 3 acceptance scenario 2
   (line 121, which states thread resolution is skipped when a session is active),
   **When** the spec is updated,
   **Then** both acceptance scenarios MUST be updated so they no longer contradict the
   new behaviour: User Story 2 scenario 1 must remove resolve-threads from the skipped
   list, and User Story 3 scenario 2 must be removed or rewritten.

---

### User Story 4 — Tests Updated to Reflect New Precondition Set (Priority: P2)

As a developer working on `ResolveThreadsAction`, I want the unit tests in
`tests/unit/cli/ci/pipeline/actions/resolve_threads/` to reflect the new precondition set
so that tests remain accurate documentation and the test suite does not contain misleading
"skip when session active" assertions.

**Why this priority**: Test accuracy is a prerequisite for CI confidence and for future
developers understanding the expected behaviour. Removing a behaviour without removing
the corresponding test leaves false confidence in outdated contracts.

**Independent Test**: Can be verified by running the test file(s) for `ResolveThreadsAction`
and confirming all tests pass and none assert `SKIP` as the result of `active_session=True`
alone (without another failing precondition).

**Acceptance Scenarios**:

1. **Given** the existing test that asserts `ActionDecision.SKIP` when
   `active_session=True` (and all other preconditions pass),
   **When** the `no_active_session` check is removed from the source,
   **Then** that test MUST be updated (or replaced) to assert `ActionDecision.EXECUTE`
   for the same snapshot, confirming the session guard is no longer in effect.

2. **Given** the test suite for `ResolveThreadsAction`,
   **When** the full suite runs with coverage enabled,
   **Then** it MUST achieve 100% line coverage on
   `agentic_devtools/cli/ci/pipeline/actions/resolve_threads.py` — covering all branches
   in both `evaluate()` and `execute()`, including the "No prior Copilot reviews found
   (race condition)" branch — with no `SKIP` branches related to the removed session
   check remaining untested.

3. **Given** that squash and dispatch-repair tests still contain "skip when session active"
   scenarios,
   **When** the resolve-threads tests are updated,
   **Then** those unrelated test files MUST NOT be modified — only the resolve-threads
   test files are in scope.

---

### Edge Cases

- **Session active AND CI failing**: The action must still skip, with the reason being
  CI failure (not the session). Removing the session guard does not affect this outcome
  because CI is the first gate in `evaluate()` after this change (the precondition
  evaluation order remains CI → pending review → unresolved threads).

- **Session active AND pending Copilot review**: The action must still skip with reason
  "Copilot review is pending on HEAD". The session state is irrelevant.

- **Session active AND no unresolved threads**: The action must skip with reason "No
  unresolved threads from prior commits". The session state is irrelevant.

- **Interaction with `dispatch-repair` and `squash`**: These two actions still require
  `no_active_session` as a precondition. The change is scoped strictly to
  `ResolveThreadsAction`; no other action class is modified.

- **`execute()` implicit gate (`r.commit_sha != snapshot.head_sha`)**: Even after removing
  the `no_active_session` check from `evaluate()`, the `execute()` method already filters
  reviews to those on commits prior to HEAD. If a session is active but no new commit has
  been pushed yet, `prior_reviews` will be empty and `execute()` returns
  `ActionDecision.SKIP` with reason "No prior Copilot reviews found (race condition)".
  This implicit gate is preserved and must not be modified.

- **Concurrent session produces the resolving commit**: A Copilot coding session may push
  a commit that addresses prior review threads. On the same loop trigger (or the next
  one), `resolve_threads` can now evaluate those threads immediately rather than waiting
  for the session to terminate. This is the primary motivating scenario and is the
  desired behaviour.

- **Downstream actions (approve, merge) affected by resolution**: `execute()` calls
  `derived.set("unresolved_threads", unresolved)` so that downstream actions in the same
  run see the post-resolution count. This remains unchanged — the session state does not
  affect whether derived state is updated.

---

## Requirements

### Functional Requirements

- **FR-001**: `ResolveThreadsAction.evaluate()` MUST NOT check `snapshot.active_session`
  as a precondition. The `no_active_session` precondition block (lines 33–41 of the
  current `evaluate()` implementation) MUST be removed entirely.

- **FR-002**: `ResolveThreadsAction.evaluate()` MUST still require `snapshot.ci_status`
  to equal `"passing"` before returning `ActionDecision.EXECUTE`. Failing CI MUST result
  in `ActionDecision.SKIP`. After FR-001 is applied, the CI check becomes the first
  precondition evaluated.

- **FR-003**: `ResolveThreadsAction.evaluate()` MUST still require
  `derived.copilot_review_pending` to be `False` before returning `ActionDecision.EXECUTE`.
  A pending Copilot review on HEAD MUST result in `ActionDecision.SKIP`.

- **FR-004**: `ResolveThreadsAction.evaluate()` MUST still require
  `snapshot.unresolved_threads > 0` before returning `ActionDecision.EXECUTE`. Zero
  unresolved threads MUST result in `ActionDecision.SKIP`.

- **FR-005**: The implicit gate in `ResolveThreadsAction.execute()` — the filter
  `r.commit_sha != snapshot.head_sha` that restricts resolution to reviews on prior
  commits — MUST be preserved unchanged. This filter ensures that only feedback from
  commits before HEAD is evaluated for resolution and is the correct mechanism for
  determining whether a new commit addressing the feedback exists.

- **FR-006**: The `ResolveThreadsAction` class docstring MUST be updated to remove
  "No active Copilot coding session" from the listed Preconditions. The remaining
  preconditions ("No pending Copilot review on HEAD" and "Unresolved threads exist from
  prior commits") MUST remain.

- **FR-007**: FR-005 in `specs/1559-refactor-loop-into-idempotent/spec.md` MUST be
  updated to remove the statement that thread resolution is skipped when a Copilot coding
  session is active. The updated FR-005 MUST continue to specify that squash and
  dispatch-repair MUST NOT execute when a Copilot coding session is active. Additionally,
  User Story 2 acceptance scenario 1 (line 93–94) MUST remove "resolve-threads" from the
  list of actions skipped when a session is active, and User Story 3 acceptance scenario 2
  (line 121) MUST be removed or rewritten so it no longer contradicts the new behaviour.

### Non-Functional Requirements

- **NFR-001**: The change MUST NOT alter the public interface of `ResolveThreadsAction`
  (`name`, `evaluate`, `execute`). No other action class, the pipeline runner, or any
  existing caller needs to be modified.

- **NFR-002**: All existing unit tests for `ResolveThreadsAction` that assert
  `ActionDecision.SKIP` solely because `active_session=True` MUST be updated so that the
  same snapshot now asserts `ActionDecision.EXECUTE`. Tests for the remaining skip
  conditions (CI failing, pending review, no threads) MUST remain and still pass.

- **NFR-003**: After the change, the test suite MUST achieve 100% line coverage on
  `agentic_devtools/cli/ci/pipeline/actions/resolve_threads.py`, including all branches
  in both `evaluate()` and `execute()` (specifically including the "No prior Copilot
  reviews found (race condition)" branch in `execute()`). No uncovered lines introduced
  or left behind.

- **NFR-004**: The change to spec 1559 MUST be minimal — only the resolve-threads
  reference in FR-005, User Story 2 acceptance scenario 1, and User Story 3 acceptance
  scenario 2 are updated. No other sections or requirements in spec 1559 are modified.

### Key Entities

- **`ResolveThreadsAction`**: The action class in
  `agentic_devtools/cli/ci/pipeline/actions/resolve_threads.py` that evaluates and
  executes resolution of unresolved Copilot review threads.

- **`PRStateSnapshot.active_session`**: Boolean field indicating whether a Copilot coding
  session is currently active for the PR. After this change, `ResolveThreadsAction` no
  longer reads this field during evaluation.

- **Implicit commit-recency gate**: The `r.commit_sha != snapshot.head_sha` filter in
  `execute()` that limits resolution to reviews from commits prior to HEAD, ensuring only
  feedback that predates the current HEAD can be resolved.

- **`specs/1559-refactor-loop-into-idempotent/spec.md` FR-005**: The functional
  requirement in the companion spec that currently governs the session-gating of
  thread-resolution, squash, and dispatch-repair. Must be reworded in place so that only
  squash and dispatch-repair retain the session guard (no renumbering).

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: `ResolveThreadsAction.evaluate()` returns `ActionDecision.EXECUTE` when
  called with a snapshot where `active_session=True`, `ci_status="passing"`,
  `copilot_review_pending=False`, and `unresolved_threads >= 1`, verified by a unit test
  that passes after the change and would have failed before.

- **SC-002**: `ResolveThreadsAction.evaluate()` still returns `ActionDecision.SKIP` when
  any of the three remaining preconditions fail (`ci_status != "passing"`,
  `copilot_review_pending=True`, or `unresolved_threads == 0`), regardless of
  `active_session`, verified by the existing skip-condition tests (updated to cover all
  combinations with both `active_session=True` and `active_session=False`).

- **SC-003**: The `"no_active_session"` key does NOT appear in the `preconditions` dict
  of any `ActionResult` returned by `ResolveThreadsAction.evaluate()`, verified by
  asserting the key is absent in unit tests after the change.

- **SC-004**: All tests in `tests/unit/cli/ci/pipeline/actions/resolve_threads/` pass
  with 100% line coverage on `resolve_threads.py`, and no regression is introduced in
  the test suites for `squash`, `dispatch_repair`, or any other action.

---

*Spec created manually for issue #1569 — the SpecKit Issue Trigger workflow failed
structural validation after 3 LLM attempts due to missing mandatory sections.*

---
*Generated by Copilot SDK (claude-opus-4.6)*
