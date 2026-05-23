# Tasks: Auto-push with --force-with-lease after Rebase (#1519)

## Phase Mapping: Plan → Tasks

| Tasks Phase | Plan Phase(s) | Description |
|---|---|---|
| Phase 1: Setup | Phase 3: Tests | Shared test-directory scaffolding needed before adding new focused coverage |
| Phase 2: Foundational | Phase 2: Add auto-push to `checkout_and_sync_branch()`, Phase 4: Documentation | Shared helper and return-shape changes that unblock story work and documentation updates |
| Phase 3: User Story 1 | Phase 1: Fix dry-run reporting in `commit_cmd()`, Phase 3: Tests | Git save workflow behavior and its story-specific validation |
| Phase 4: User Story 2 | Phase 2: Add auto-push to `checkout_and_sync_branch()`, Phase 3: Tests | PR review workflow behavior and its story-specific validation |
| Phase 5: User Story 3 | Phase 2: Add auto-push to `checkout_and_sync_branch()`, Phase 3: Tests | Graceful push-failure handling and its story-specific validation |
| Phase 6: Polish & Cross-Cutting | Phase 3: Tests, Phase 4: Documentation | Final validation, compatibility updates, and docstring polish |

## Phase 1: Setup

- [ ] T001 [US2] Create test directory structure for new test files (`tests/unit/cli/azure_devops/review_commands/` with `__init__.py` files) (FR-2)

## Phase 2: Foundational — Helper Function & Return Type Extension

- [ ] T002 Create `_try_force_push_after_rebase(dry_run: bool) -> bool | None` helper in `agentic_devtools/cli/azure_devops/review_commands.py` that wraps `force_push()` with `SystemExit` catch (FR-6,
  FR-7); on failure prints warning that rebase succeeded but push failed with guidance for manual `git push --force-with-lease`
- [ ] T003 Extend `checkout_and_sync_branch()` return type from `tuple[bool, str | None, set[str], bool]` to
  `tuple[bool, str | None, set[str], bool, bool | None]` with fifth element `push_succeeded` (FR-2);
  update docstring and all return statements to include `None` default
- [ ] T004 Update the `checkout_and_sync_branch()` call inside `setup_pull_request_review()` in `agentic_devtools/cli/azure_devops/review_commands.py` to unpack the fifth return element (NFR-1)
- [ ] T005 [US2] Update any other callers of `checkout_and_sync_branch()` (e.g., async wrappers, test mocks) to handle the new 5-element return tuple (FR-2, NFR-1)

## Phase 3: User Story 1 — Auto-push in Git Save Workflow (P1)

- [ ] T006 [P] [US1] Write failing tests in `tests/unit/cli/git/commands/test_commit_cmd.py` for dry-run mode reporting push intent when `needs_force_push=True` (SC-3, FR-5)
- [ ] T007 [P] [US1] Write failing tests in `tests/unit/cli/git/commands/test_commit_cmd.py` for dry-run mode reporting publish intent when `needs_force_push=False` (SC-3, FR-5)
- [ ] T008 [US1] Fix dry-run reporting gap in `commit_cmd()` in `agentic_devtools/cli/git/commands.py`: when `dry_run=True` and `not skip_push`, call `force_push(dry_run=True)` or
  `publish_branch(dry_run=True)` based on `needs_force_push` before printing summary (FR-1, FR-5)
- [ ] T009 [US1] Write happy-path tests in `tests/unit/cli/git/commands/test__sync_with_main.py` verifying `force_push()` is called exactly once after
  successful rebase and zero times when no rebase occurred
  (SC-1, FR-1, FR-3, FR-4)
- [ ] T010 [US1] Verify existing behavior in `commit_cmd()` that `force_push()` is called when `rebase_occurred=True` — ensure no regression (FR-1, FR-6)

## Phase 4: User Story 2 — Auto-push in PR Review Workflow (P1)

- [ ] T011 [P] [US2] Write failing test: successful rebase (`is_success=True`, `was_rebased=True`) triggers `force_push()` and returns `push_succeeded=True` in
  `tests/unit/cli/azure_devops/review_commands/test_checkout_and_sync_branch.py` (SC-2, FR-2)
- [ ] T012 [P] [US2] Write failing test: no rebase needed (`was_rebased=False`) returns `push_succeeded=None` and does not call `force_push()` in
  `tests/unit/cli/azure_devops/review_commands/test_checkout_and_sync_branch.py` (SC-2, FR-3, FR-4)
- [ ] T013 [P] [US2] Write failing test: rebase conflicts (`had_rebase_conflicts=True`) returns `push_succeeded=None` and does not call `force_push()` in
  `tests/unit/cli/azure_devops/review_commands/test_checkout_and_sync_branch.py` (SC-2, FR-3)
- [ ] T014 [P] [US2] Write failing test: fetch failed returns `push_succeeded=None` and does not call `force_push()` in `tests/unit/cli/azure_devops/review_commands/test_checkout_and_sync_branch.py`
  (SC-2, FR-3)
- [ ] T015 [P] [US2] Write failing test: `skip_rebase` conditions return `push_succeeded=None` in `tests/unit/cli/azure_devops/review_commands/test_checkout_and_sync_branch.py` (FR-3)
- [ ] T016 [P] [US2] Write failing test: dry-run calls `force_push(dry_run=True)` and returns `push_succeeded=None` in `tests/unit/cli/azure_devops/review_commands/test_checkout_and_sync_branch.py`
  (SC-3, FR-5)
- [ ] T017 [US2] Implement auto-push logic in `checkout_and_sync_branch()`: after successful rebase (`rebase_result.is_success and rebase_result.was_rebased`), call
  `_try_force_push_after_rebase(dry_run)` and set `push_succeeded` (FR-2, FR-3, FR-4, FR-5, FR-6)
- [ ] T018 [US2] Verify all tests from T011–T016 pass (green phase)

## Phase 5: User Story 3 — Graceful Push Failure Handling (P2)

- [ ] T019 [P] [US3] Write failing test: `SystemExit` from `force_push()` is caught, prints warning message distinguishing rebase success from push failure, and returns `push_succeeded=False` in
  `tests/unit/cli/azure_devops/review_commands/test_checkout_and_sync_branch.py` (SC-4, FR-7)
- [ ] T020 [P] [US3] Write failing test: workflow continues after push failure (no exception propagated) and includes guidance for manual intervention in output (SC-4, FR-7)
- [ ] T021 [P] [US3] Write test: when no push is attempted (`push_succeeded=None`), no push failure message is displayed (SC-4, FR-7)
- [ ] T022 [US3] Verify `_try_force_push_after_rebase()` implementation handles `SystemExit` correctly — prints "Rebase succeeded but push failed" with manual `git push --force-with-lease` guidance
  and returns `False` (FR-7)
- [ ] T023 [US3] Verify all tests from T019–T021 pass (green phase)

## Phase 6: Polish & Cross-Cutting

- [ ] T024 [P] Update docstring for `checkout_and_sync_branch()` to document the new `push_succeeded` return element and auto-push behavior
- [ ] T025 [P] Update docstring for `commit_cmd()` to document dry-run push reporting behavior
- [ ] T026 Run full test suite (`agdt-test`) and verify no regressions across FR-1, FR-2, and FR-7
- [ ] T027 Run `python scripts/validate_test_structure.py` to confirm 1:1:1 test structure compliance for FR-1, FR-2, and FR-7 coverage
- [ ] T028 Run `bash scripts/run-pr-checks.sh` to verify all CI-blocking checks pass for the FR-1, FR-2, and FR-7 implementation
- [ ] T029 [US2] Update existing tests in `tests/azure_devops/test_review_commands.py` that mock `checkout_and_sync_branch` to handle the new 5-element return tuple (FR-2, NFR-1)

## Dependencies

```text
T001 → T006, T007, T009, T011–T016, T019–T021
T002 → T017, T022
T003 → T004, T005, T017
T004 + T005 → T029
T006 + T007 → T008
T008 → T010
T011–T016 → T017 → T018
T019–T021 → T022 → T023
T018 + T023 → T026
T026 → T027 → T028
```

---
*Generated by Copilot SDK (claude-opus-4.6)*
