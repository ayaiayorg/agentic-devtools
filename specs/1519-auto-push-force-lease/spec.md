# Spec: Auto-push with --force-with-lease after successful rebase onto origin/main

**Source Issue**: [#1519](https://github.com/ayaiayorg/agentic-devtools/issues/1519)

## Problem Statement

Users currently have workflows that rebase a local branch onto `origin/main`, but they
must manually remember to push the rebased branch afterward. Because rebasing rewrites
commit history, a normal push may be rejected and the correct follow-up action is
typically a safe force push using `--force-with-lease`. This creates friction in both
the git save workflow and the PR review workflow, increases the chance that remote
branches remain stale after a successful rebase, and can lead to user confusion about
whether local changes have been published.

The feature should automatically perform a `--force-with-lease` push after a successful
rebase onto `origin/main` in the relevant workflows, while avoiding unnecessary pushes,
respecting dry-run behavior, and handling push failures gracefully. The implementation
should reuse the existing `force_push()` function rather than introducing new git push
logic.

## Clarifications

### Session 2026-05-23

- Q: The git save workflow (`commit_cmd()` in
  `agentic_devtools/cli/git/commands.py`) already calls `force_push()`
  after `_sync_with_main()` returns `True`.
  Does FR-1 refer to ensuring this existing behavior is tested and documented,
  or is there a code path where a successful rebase in `_sync_with_main()`
  does NOT currently trigger a force push? → A: The existing git save workflow
  already handles force push after rebase in `commit_cmd()`. FR-1 confirms
  this behavior must remain correct and be explicitly tested. The primary new
  code change for the git save workflow is ensuring that the `_sync_with_main()`
  path in `commit_cmd()` remains correct and that dry-run mode reports the
  intended push (currently it does not report the auto-push in dry-run because
  the dry-run branch only says "No changes were made" without mentioning the
  push that would have occurred). The main net-new implementation is in the PR
  review workflow (`checkout_and_sync_branch`).

- Q: For `checkout_and_sync_branch()`, should the auto force push happen
  inside the function itself, or should the function return a signal
  (e.g., `was_rebased`) so the caller can invoke force push? → A: The auto
  force push should happen inside `checkout_and_sync_branch()` itself,
  immediately after the successful rebase (after line 202 where it prints
  "Branch is synced with main."). This keeps the push logic co-located with
  the rebase logic and avoids requiring all callers to add push handling. The
  return tuple should be extended with a fifth element
  `push_succeeded: bool | None` (None = no push attempted, True = pushed,
  False = push failed).

- Q: Should auto-push occur after a rebase that had conflicts
  (i.e., `had_rebase_conflicts=True` in `checkout_and_sync_branch`)?
  The current code continues the review even on conflicts. → A: No.
  Auto-push must NOT occur when `had_rebase_conflicts=True` or when the
  rebase was not successful (`rebase_result.is_success=False`). Pushing a
  conflict-ridden state to the remote would be harmful. Only a clean,
  successful rebase (where `rebase_result.is_success=True` and
  `rebase_result.was_rebased=True`) should trigger auto-push.

- Q: The existing `force_push()` function raises an exception (via `run_git`)
  on failure rather than returning a result. How should push failures be
  handled gracefully per FR-7? → A: In current code, `run_git(..., check=True)`
  exits via `SystemExit` on git failure, so FR-7 must account for that actual
  failure mode. The implementation should either catch `SystemExit` at the
  auto-push call site, or update the push pathway to use a non-exiting call
  (`check=False`) and handle the non-zero return code explicitly. In either
  approach, on failure print a clear warning that the rebase succeeded but the
  push failed, log error details, continue the workflow without aborting, and
  set `push_succeeded=False`.

- Q: For dry-run mode in `checkout_and_sync_branch()`, should the function call
  `force_push(dry_run=True)` (which prints "[DRY RUN] Would force push") or
  handle the messaging separately? → A: The function should call
  `force_push(dry_run=True)` directly, which already prints the appropriate
  dry-run message. This reuses existing logic and keeps behavior consistent
  with the git save workflow's dry-run handling.

## User Scenarios & Testing

### User Story 1 - Auto-push after successful sync in git save workflow (P1)

As a user running the git save workflow, I want the branch to be automatically
force-pushed with lease after a successful rebase onto `origin/main`, so that my remote
branch stays aligned with the rebased local branch without requiring a manual follow-up
command.

**Applies to:** FR-1, FR-3, FR-4, FR-5, FR-6

**Acceptance scenarios**

1. **Given** `_sync_with_main()` rebases the current branch onto `origin/main`
   successfully and the branch now differs from its remote counterpart, **when** the
   workflow completes, **then** the system invokes the existing `force_push()` behavior
   for the current branch.
2. **Given** `_sync_with_main()` determines that no push is needed because no
   rebase occurred or the remote is already up to date, **when** the workflow
   completes, **then** no force push is attempted.
3. **Given** the command is executed in dry-run mode, **when**
   `_sync_with_main()` would otherwise auto-push, **then** the system reports
   that a force push would occur but does not modify the remote branch.

### User Story 2 - Auto-push after successful sync in PR review workflow (P1)

As a user running the PR review workflow, I want the branch to be automatically
force-pushed with lease after `checkout_and_sync_branch()` successfully rebases onto
`origin/main`, so that the reviewed branch is immediately updated on the remote after
history is rewritten.

**Applies to:** FR-2, FR-3, FR-4, FR-5, FR-6

**Acceptance scenarios**

1. **Given** `checkout_and_sync_branch()` checks out a branch and successfully rebases it
   onto `origin/main` (with `rebase_result.is_success=True` and `rebase_result.was_rebased=True`), **when** the branch has rewritten local history that must be
   published, **then** the system invokes the existing `force_push()` behavior for that
   branch.
2. **Given** `checkout_and_sync_branch()` does not perform a successful rebase
   (including cases where rebase conflicts occurred, fetch failed, or
   skip_rebase conditions apply), **when** the workflow exits, **then** no
   automatic force push is attempted.
3. **Given** dry-run mode is enabled, **when**
   `checkout_and_sync_branch()` would otherwise auto-push, **then** the system
   calls `force_push(dry_run=True)` which logs the intended push without
   contacting the remote.

### User Story 3 - Graceful handling of push failures (P2)

As a user, I want auto-push failures to be reported clearly without causing unnecessary data loss or misleading success messages, so that I can recover manually if the remote push does not succeed.

**Applies to:** FR-7

**Acceptance scenarios**

1. **Given** a successful rebase is followed by an auto-push attempt and the
   push fails (currently surfaced via `SystemExit` from
   `run_git(..., check=True)` unless the push path is made non-exiting),
   **when** the workflow handles the error, **then** the user is informed that
   the rebase succeeded but the push failed.
2. **Given** an auto-push fails for a recoverable remote reason, **when** the workflow
   completes, **then** the local branch remains rebased, the workflow does not abort or
   fail solely because of the push error, and the failure is treated as non-silent with
   guidance that manual intervention may be required.
3. **Given** no push was attempted, **when** the workflow reports completion,
   **then** it must not display an auto-push failure message.

## Requirements

### Functional Requirements

- **FR-1:** The system must automatically invoke the existing `force_push()`
  function
  after `_sync_with_main()` completes a successful rebase of the current branch onto
  `origin/main`, when a remote update is required. (Note: this behavior already
  exists in `commit_cmd()` in `agentic_devtools/cli/git/commands.py`; this
  requirement ensures it remains correct and that dry-run mode reports the
  intended push action.)
- **FR-2:** The system must automatically invoke the existing `force_push()` function
  after `checkout_and_sync_branch()` completes a successful rebase of the target branch
  onto `origin/main`, when a remote update is required. The force push call
  must occur inside `checkout_and_sync_branch()` itself, immediately after a
  clean successful rebase (`rebase_result.is_success=True` and
  `rebase_result.was_rebased=True`). The return tuple must be extended with a
  fifth element `push_succeeded: bool | None` (None = no push attempted,
  True = pushed, False = push failed).
- **FR-3:** The system must not attempt an automatic force push if no successful
  rebase onto `origin/main` occurred. This includes cases where: rebase was
  skipped, fetch failed, rebase had conflicts (`had_rebase_conflicts=True`),
  or rebase returned `was_rebased=False`.
- **FR-4:** The system must not attempt an automatic force push when the operation would
  be a no-op, including cases where the remote branch is already aligned with the
  rebased local state or no publishable branch update exists.
- **FR-5:** The system must respect dry-run mode by calling
  `force_push(dry_run=True)` which reports the intended `--force-with-lease`
  push without performing any remote-modifying git operation.
- **FR-6:** The system must reuse the existing `force_push()` function in
  `agentic_devtools/cli/git/operations.py` for auto-push behavior rather than
  introducing a separate implementation of force-push git logic.
- **FR-7:** The system must handle push failures from the existing push path in
  a non-fatal way (with current behavior this means handling `SystemExit` from
  `run_git(..., check=True)`, or equivalently using a non-exiting push call and
  checking its result), surface push failures clearly to the user
  distinguishing between rebase success and push failure, provide guidance that
  manual intervention may be required, and not abort the overall workflow
  solely because the auto-push failed.

### Non-Functional Requirements

- **NFR-1:** The feature must preserve existing workflow behavior except for the
  addition of the automatic post-rebase push behavior in
  `checkout_and_sync_branch()` and improved dry-run reporting in the git save
  workflow. All existing callers of `checkout_and_sync_branch()` must be
  updated to handle the new fifth return tuple element.
- **NFR-2:** The implementation must use `--force-with-lease` semantics via the
  existing `force_push()` pathway and must not degrade push safety by switching
  to a less safe force strategy.
- **NFR-3:** User-facing messaging for auto-push actions and failures must be
  clear enough for a user to determine whether the rebase succeeded, whether a
  push was attempted, and whether manual action is required. Specifically:
  success messaging must clearly indicate remote update success (for example,
  existing `force_push()` messages like `"Force pushing changes..."` and
  `"Changes pushed successfully."` are acceptable). Failure messaging must
  clearly indicate that rebase succeeded but push failed and include guidance
  to run `git push --force-with-lease` manually.
- **NFR-4:** The specification and resulting implementation must remain compatible with later SpecKit planning/task extraction by using explicit mandatory sections and concrete requirement entries.

## Success Criteria

- **SC-1:** In test coverage for `_sync_with_main()`, a successful rebase onto `origin/main` results in exactly one call to `force_push()` when a remote update is needed, and zero calls otherwise.
- **SC-2:** In test coverage for `checkout_and_sync_branch()`, a successful
  rebase onto `origin/main` (with `rebase_result.is_success=True` and `rebase_result.was_rebased=True`) results in exactly one call to `force_push()` when a
  remote update is needed, and zero calls otherwise. The test must also verify the return tuple contains the correct `push_succeeded` value.
- **SC-3:** In dry-run test scenarios for both workflows, zero remote-modifying push operations are executed and the intended auto-push is reported to the user via `force_push(dry_run=True)`.
- **SC-4:** In push-failure test scenarios, the workflow reports that the push failed,
  preserves the fact that the rebase succeeded, and does not fail the overall workflow
  solely due to the push error, with no false success message indicating the remote
  branch was updated. The `push_succeeded` return value must be `False` in the PR review workflow.
- **SC-5:** The spec passes repository validation that checks for mandatory
  SpecKit sections, including `## Problem Statement`,
  `## User Scenarios & Testing`, `## Requirements`, and
  `## Success Criteria`.

---
*Generated by Copilot SDK (claude-opus-4.6)*
