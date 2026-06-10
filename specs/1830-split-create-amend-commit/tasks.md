# Tasks: Split Create vs. Amend Commit Title Parameters & Transparency Logging

## Phase Mapping: Plan → Tasks

| Tasks Phase | Plan Phase(s) | Description |
|---|---|---|
| Phase 1: Setup | — | Scaffolding only — no direct plan equivalent |
| Phase 2: Foundational | Phase 1: Transparency Logging Infrastructure | Core logging helper functions |
| Phase 3: US1 & 2 — Intent Resolution | Phase 2: Message Resolution Logic | `CommitIntent` dataclass + `resolve_commit_intent()` |
| Phase 4: US1 — Create Path | Phase 3: Integrate New Params into `commit_cmd` | `--commit-message-title` flag + create routing |
| Phase 5: US2 — Overwrite Path | Phase 3: Integrate New Params into `commit_cmd` | `--overwrite-commit-message-title` flag + amend routing |
| Phase 6: US3 — All-Path Logging | Phases 1 + 3 | Ensure transparency helpers fire on every code path |
| Phase 7: US4 — Before/After Diff | Phases 1 + 3 | Before/after title diff in `amend_commit` |
| Phase 8: US5 — State Keys | Phase 5: State Keys & Documentation | State key constants + `commit_cmd` state fallback |
| Phase 9: US6 — Backward Compat | Phase 3: Integrate New Params into `commit_cmd` | Legacy `commit_message` path regression tests |
| Phase 10: FR-007 — `amend_cmd` | Phase 4: Update `amend_cmd` | Transparency logging for standalone amend command |
| Phase 11: Polish & Cross-Cutting | Phases 5 + 6: State Keys & Final Validation | Docstrings, docs, full test suite, lint/coverage checks |

## Phase 1: Setup

- [ ] T001 Create `agentic_devtools/cli/git/transparency.py` with module docstring and empty file scaffold
- [ ] T002 Create test directory `tests/unit/cli/git/transparency/` with `__init__.py` (FR-004, FR-005)
- [ ] T003 Create `agentic_devtools/cli/git/commit_intent.py` with module docstring and empty file scaffold
- [ ] T004 Create test directory `tests/unit/cli/git/commit_intent/` with `__init__.py` (FR-001, FR-002)

## Phase 2: Foundational — Transparency Logging Helpers (FR-004, FR-005)

- [ ] T005 Write failing tests for `print_resolved_commit_message()` in `tests/unit/cli/git/transparency/test_print_resolved_commit_message.py` — verify canonical `--- Resolved Commit Message ---` /
  `---` delimiter output (FR-004)
- [ ] T006 Write failing tests for `print_commit_title_change()` in `tests/unit/cli/git/transparency/test_print_commit_title_change.py` — verify canonical `--- Commit Title Change ---` / `---`
  delimiter output with `- old` / `+ new` format (FR-005)
- [ ] T007 Implement `print_resolved_commit_message(message: str)` in `agentic_devtools/cli/git/transparency.py` (FR-004)
- [ ] T008 Implement `print_commit_title_change(old_title: str, new_title: str)` in `agentic_devtools/cli/git/transparency.py` (FR-005)
- [ ] T009 Run tests to confirm T005/T006 pass: `agdt-test-pattern tests/unit/cli/git/transparency/ -v` (FR-004, FR-005)

## Phase 3: User Story 1 & 2 — Intent Resolution & Conflict Detection (P1)

- [ ] T010 [US1] Write failing tests for `CommitIntent` dataclass in `tests/unit/cli/git/commit_intent/test_commitintent.py`
- [ ] T011 [US1] Write failing tests for `resolve_commit_intent()` create-path in `tests/unit/cli/git/commit_intent/test_resolve_commit_intent.py` — covers title from CLI flag, body from
  `commit_message`, exit 1 when no body source available (FR-001)
- [ ] T012 [US2] Write failing tests for `resolve_commit_intent()` overwrite-path in `tests/unit/cli/git/commit_intent/test_resolve_commit_intent.py` — covers overwrite flag, exit 1 when no commits
  ahead (FR-002)
- [ ] T013 [US1] [US2] Write failing tests for conflict detection in `tests/unit/cli/git/commit_intent/test_resolve_commit_intent.py` — both CLI, both state, mixed CLI+state conflicts (FR-001, FR-002)
- [ ] T014 [US1] Implement `CommitIntent` dataclass in `agentic_devtools/cli/git/commit_intent.py`
- [ ] T015 [US1] [US2] Implement `resolve_commit_intent()` function with conflict detection, create-path validation, and overwrite-path validation in `agentic_devtools/cli/git/commit_intent.py`
  (FR-001, FR-002)
- [ ] T016 Run tests to confirm T010-T013 pass: `agdt-test-pattern tests/unit/cli/git/commit_intent/ -v` (FR-001, FR-002)

## Phase 4: User Story 1 — New Commit via `--commit-message-title` (P1)

- [ ] T017 [US1] Write failing tests for `commit_cmd` new `--commit-message-title` flag in `tests/unit/cli/git/commands/test_commit_cmd.py` — verify creates commit, prints resolved message (FR-001,
  FR-004)
- [ ] T018 [US1] Write failing tests for `--commit-message-title` rejection when branch has commits ahead in `tests/unit/cli/git/commands/test_commit_cmd.py` (FR-001)
- [ ] T019 [US1] Add `--commit-message-title` argparse argument to `commit_cmd()` in `agentic_devtools/cli/git/commands.py` (FR-001)
- [ ] T020 [US1] Integrate `resolve_commit_intent()` into `commit_cmd()` routing logic — create-path calls `create_commit` with transparency logging in `agentic_devtools/cli/git/commands.py` (FR-001,
  FR-004)
- [ ] T021 [US1] Add `print_resolved_commit_message()` call to `create_commit()` in `agentic_devtools/cli/git/operations.py` before git execution (FR-004)
- [ ] T022 [US1] Run tests: `agdt-test-pattern tests/unit/cli/git/commands/test_commit_cmd.py -v` (FR-001, FR-004)

## Phase 5: User Story 2 — Amend via `--overwrite-commit-message-title` (P1)

- [ ] T023 [US2] Write failing tests for `commit_cmd` new `--overwrite-commit-message-title` flag in `tests/unit/cli/git/commands/test_commit_cmd.py` — verify amends, prints title diff and resolved
  message (FR-002, FR-005)
- [ ] T024 [US2] Write failing tests for `--overwrite-commit-message-title` rejection when no commits ahead in `tests/unit/cli/git/commands/test_commit_cmd.py` (FR-002)
- [ ] T025 [US2] Write failing tests for body preservation during title-only overwrite in `tests/unit/cli/git/commands/test_commit_cmd.py` (FR-002)
- [ ] T026 [US2] Add `--overwrite-commit-message-title` argparse argument to `commit_cmd()` in `agentic_devtools/cli/git/commands.py` (FR-002)
- [ ] T027 [US2] Integrate overwrite-path into `commit_cmd()` — reads old title via `get_last_commit_message()`, replaces title only, preserves body in `agentic_devtools/cli/git/commands.py` (FR-002,
  FR-005)
- [ ] T028 [US2] Add `print_commit_title_change()` and `print_resolved_commit_message()` calls to `amend_commit()` in `agentic_devtools/cli/git/operations.py` before git execution (FR-004, FR-005)
- [ ] T029 [US2] Run tests: `agdt-test-pattern tests/unit/cli/git/commands/test_commit_cmd.py -v` (FR-002, FR-004, FR-005)

## Phase 6: User Story 3 — Transparency Logging on All Paths (P1)

- [ ] T030 [US3] Write failing tests verifying `create_commit` prints resolved message in canonical format before git execution in `tests/unit/cli/git/operations/test_create_commit.py` (FR-004)
- [ ] T031 [US3] Write failing tests verifying `amend_commit` prints resolved message in canonical format before git execution in `tests/unit/cli/git/operations/test_amend_commit.py` (FR-004, FR-005)
- [ ] T032 [US3] Write failing tests verifying transparency logging in dry-run mode (message printed, git suppressed) in `tests/unit/cli/git/commands/test_commit_cmd.py` (FR-004)
- [ ] T033 [US3] Ensure `create_commit` and `amend_commit` always call transparency helpers regardless of how they are invoked (legacy or new paths) in `agentic_devtools/cli/git/operations.py`
  (FR-004, FR-005)
- [ ] T034 [US3] Run tests: `agdt-test-pattern tests/unit/cli/git/operations/ -v`

## Phase 7: User Story 4 — Before/After Diff on Amend (P1)

- [ ] T035 [US4] Write failing tests for before/after title diff when old and new titles are identical in `tests/unit/cli/git/operations/test_amend_commit.py` (FR-005)
- [ ] T036 [US4] Write failing tests for before/after title diff when `--overwrite-commit-message-title` used with no commits ahead (exit 1, no partial output) in
  `tests/unit/cli/git/commands/test_commit_cmd.py` (FR-005)
- [ ] T037 [US4] Verify `print_commit_title_change` is called even when titles match in `agentic_devtools/cli/git/operations.py` (FR-005)
- [ ] T038 [US4] Run tests: `agdt-test-pattern tests/unit/cli/git/ -v` (FR-005)

## Phase 8: User Story 5 — State Key Equivalents (P2)

- [ ] T039 [P] [US5] Add `STATE_COMMIT_MESSAGE_TITLE` and `STATE_OVERWRITE_COMMIT_MESSAGE_TITLE` constants to `agentic_devtools/cli/git/core.py` (FR-003)
- [ ] T040 [US5] Write failing tests for state key fallback when no CLI flags provided in `tests/unit/cli/git/commit_intent/test_resolve_commit_intent.py` (FR-003)
- [ ] T041 [US5] Write failing tests for CLI flag precedence over state key in `tests/unit/cli/git/commit_intent/test_resolve_commit_intent.py` (FR-003)
- [ ] T042 [US5] Update `commit_cmd()` to read `commit_message_title` and `overwrite_commit_message_title` from state when CLI flags absent in `agentic_devtools/cli/git/commands.py` (FR-003)
- [ ] T043 [US5] Run tests: `agdt-test-pattern tests/unit/cli/git/commit_intent/ -v` (FR-003)

## Phase 9: User Story 6 — Backward Compatibility (P2)

- [ ] T044 [US6] Write tests verifying legacy `commit_message` state key path is unchanged when no new flags are present in `tests/unit/cli/git/commands/test_commit_cmd.py` (FR-006)
- [ ] T045 [US6] Write tests verifying `--commit-message` CLI flag continues to work with heuristic amend detection in `tests/unit/cli/git/commands/test_commit_cmd.py` (FR-006)
- [ ] T046 [US6] Write tests verifying `should_amend_instead_of_commit` remains the default decision path in `tests/unit/cli/git/commands/test_commit_cmd.py` (FR-006)
- [ ] T047 [US6] Run existing test suite to confirm no regressions: `agdt-test-pattern tests/unit/cli/git/ -v` (FR-006)

## Phase 10: FR-007 — `amend_cmd` Transparency Logging

- [ ] T048 [US3] Write failing unit tests for `amend_cmd` transparency logging — happy-path (before/after title diff and resolved message printed in canonical format)
  and negative cases (no commits ahead exits without partial output) in `tests/unit/cli/git/commands/test_amend_cmd.py` (FR-007)
- [ ] T049 [US3] Update `_do_amend()` / `amend_cmd()` to read old title via `get_last_commit_message()` and call transparency helpers in `agentic_devtools/cli/git/commands.py` (FR-007)
- [ ] T050 [US3] Run tests: `agdt-test-pattern tests/unit/cli/git/commands/test_amend_cmd.py -v` (FR-007)

## Phase 11: Polish & Cross-Cutting

- [ ] T051 [P] Update `commit_cmd()` docstring with new CLI flags, state keys, and logging behavior in `agentic_devtools/cli/git/commands.py` (FR-008)
- [ ] T052 [P] Update `amend_cmd()` docstring with transparency logging documentation in `agentic_devtools/cli/git/commands.py` (FR-008)
- [ ] T053 [P] Update `.github/copilot-instructions.md` Git Workflow section to document `--commit-message-title`, `--overwrite-commit-message-title`, and transparency output format (FR-008, NFR-003)
- [ ] T054 Run full test suite with coverage: `agdt-test` + `agdt-task-wait` (NFR-002, FR-006)
- [ ] T055 Run `agdt-test-pattern tests/unit/cli/git/commands/ -v` to verify command tests pass; coverage enforced by `scripts/targeted-checks.sh` (NFR-002, FR-006)
- [ ] T056 Run `agdt-test-pattern tests/unit/cli/git/operations/ -v` to verify operations tests pass; coverage enforced by `scripts/targeted-checks.sh` (NFR-002, FR-004, FR-005)
- [ ] T057 Run `agdt-test-pattern tests/unit/cli/git/transparency/ -v` to verify transparency tests pass; coverage enforced by `scripts/targeted-checks.sh` (NFR-002, FR-004, FR-005)
- [ ] T058 Run `agdt-test-pattern tests/unit/cli/git/commit_intent/ -v` to verify commit intent tests pass; coverage enforced by `scripts/targeted-checks.sh` (NFR-002, FR-001, FR-002, FR-003)
- [ ] T059 Run `bash scripts/targeted-checks.sh` for ruff format, ruff check, markdownlint, mypy
- [ ] T060 Run `python scripts/validate_test_structure.py` to verify 1:1:1 test structure compliance (FR-006)
- [ ] T061 Final commit via `agdt-git-save-work`
- [ ] T062 [P] Verify `.github/copilot-instructions.md` documents `--commit-message-title`, `--overwrite-commit-message-title`, and transparency output format (FR-008)

## Dependency Graph

```text
T001-T004 (setup) → T005-T009 (transparency helpers)
T005-T009 → T010-T016 (intent resolution)
T010-T016 → T017-T022 (US1: create path)
T010-T016 → T023-T029 (US2: overwrite path)
T017-T029 → T030-T034 (US3: all-path logging)
T030-T034 → T035-T038 (US4: diff on amend)
T010-T016 → T039-T043 (US5: state keys)
T017-T029 → T044-T047 (US6: backward compat)
T030-T034 → T048-T050 (FR-007: amend_cmd)
All above → T051-T062 (polish)
```

## FR → Task Mapping

| FR | Tasks |
|---|---|
| FR-001 | T004, T011, T013, T015, T016, T017, T018, T019, T020, T022, T058 |
| FR-002 | T004, T012, T013, T015, T016, T023, T024, T025, T026, T027, T029, T058 |
| FR-003 | T039, T040, T041, T042, T043, T058 |
| FR-004 | T002, T005, T007, T009, T017, T020, T021, T022, T028, T029, T030, T032, T033, T056, T057 |
| FR-005 | T002, T006, T008, T009, T023, T028, T029, T031, T033, T035, T036, T037, T038, T056, T057 |
| FR-006 | T044, T045, T046, T047, T054, T055, T060 |
| FR-007 | T048, T049, T050 |
| FR-008 | T051, T052, T053, T062 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
