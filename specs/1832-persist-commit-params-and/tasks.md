# Tasks: Persist Commit Params and Rendered Messages to State

## Phase Mapping: Plan → Tasks

| Tasks Phase | Plan Phase(s) | Description |
|---|---|---|
| Phase 1: Setup | — | Test scaffolding (no direct plan equivalent) |
| Phase 2: Foundational | Plan Phase 1 | Implement `_extract_commit_parts()` helper |
| Phase 3: User Story 1 | Plan Phases 2, 3, 4 | Persistence function, fallback logic, `commit_cmd` integration |
| Phase 4: User Story 2 | Plan Phase 4 | Full-message and body persistence tests |
| Phase 5: User Story 3 | Plan Phase 4 | Title persistence across amends |
| Phase 6: User Story 4 | Plan Phase 4 | Session recovery persistence contract |
| Final Phase: Polish | Plan Phases 5, 6 | Documentation update + validation & CI |

## Phase 1: Setup

- [ ] T001 [US1] Create test directory `tests/unit/cli/git/commands/` `__init__.py` if missing, and create empty test files for new symbols: `test__extract_commit_parts.py`,
  `test__persist_commit_metadata.py`

## Phase 2: Foundational — Helper Functions

- [ ] T002 Implement `_extract_commit_parts(message: str) -> tuple[str, str]` in `agentic_devtools/cli/git/commands.py` — pure function that splits commit message into title (first line) and body
  (remainder with leading blank separator stripped); satisfies title extraction for FR-001 and body extraction for FR-003
- [ ] T003 [P] Write unit tests in `tests/unit/cli/git/commands/test__extract_commit_parts.py` covering: title-only message yields empty body (FR-003), title+blank+body, title+blank+multiline body
  with footer, title+body without blank separator, empty string edge case, whitespace preservation (NFR-002)

## Phase 3: User Story 1 — Agent Reuses Commit Title for PR Creation (P1)

- [ ] T004 Implement `_persist_commit_metadata(message: str) -> None` in `agentic_devtools/cli/git/commands.py` — uses `read_modify_write_state()` to atomically write all 4 keys
  (`commit_message_title`, `git.last_commit_title`, `git.last_commit_message`, `git.last_commit_body`) satisfying FR-001, FR-002, FR-003, FR-006, FR-007
- [ ] T005 [P] [US1] Write unit tests in `tests/unit/cli/git/commands/test__persist_commit_metadata.py` covering: success scenario — all 4 keys written correctly (FR-008), overwrite of existing values
  (FR-006), exact message preservation with special chars (NFR-002), title-only produces empty body string (FR-003), atomic write via `read_modify_write_state` mock (FR-007)
- [ ] T006 [US1] Integrate `_persist_commit_metadata()` call into `commit_cmd()` in `agentic_devtools/cli/git/commands.py` — call after successful `create_commit()`/`amend_commit()` and before
  `_sync_with_main()`, gated by `not dry_run` (satisfies FR-004, FR-005, FR-009)
- [ ] T007 [US1] Implement fallback logic in `commit_cmd()` in `agentic_devtools/cli/git/commands.py` — when no `--commit-message` CLI arg and `commit_message` state is empty, read
  `git.last_commit_message` from state as default message (FR-001); keeps `get_commit_message()` in `core.py` unchanged
- [ ] T008 [US1] Write/extend tests in `tests/unit/cli/git/commands/test_commit_cmd.py` covering: success scenario — state keys populated after successful commit (FR-001, FR-002), state keys NOT
  written during dry-run (FR-005), state keys NOT written when commit fails (FR-004), fallback fires when `commit_message` empty but `git.last_commit_message` exists (FR-001), fallback does NOT fire
  when `commit_message` is set, fallback does NOT fire when `--commit-message` CLI arg provided, `sys.exit(1)` when both empty, keys readable via standard `agdt-get` pattern (FR-008)
- [ ] T009 [US1] Verify `commit_message_title` is output-only metadata — nominal scenario: add explicit assertion in test that `should_amend_instead_of_commit()` does not read `commit_message_title`
  (FR-009); also verify `agdt-git-save-work` does NOT use it as create/amend intent signal

## Phase 4: User Story 2 — Debugging Last Commit (P2)

- [ ] T010 [US2] Write tests in `tests/unit/cli/git/commands/test_commit_cmd.py` verifying: multi-line message with title+body+footer stored verbatim in `git.last_commit_message` (FR-002, NFR-002),
  title-only message sets `git.last_commit_body` to empty string not null (FR-003), amend path overwrites both `git.last_commit_message` and `git.last_commit_body` (FR-006)

## Phase 5: User Story 3 — Title Persistence Across Amends (P2)

- [ ] T011 [US3] Write tests in `tests/unit/cli/git/commands/test_commit_cmd.py` verifying: two successive amends with same title keep `git.last_commit_title` stable (FR-006), amend with changed title
  updates `git.last_commit_title` to new value (FR-006)

## Phase 6: User Story 4 — Session Recovery After Crash (P3)

- [ ] T012 [US4] Write tests verifying: state keys (`git.last_commit_message`, `git.last_commit_title`) survive process boundaries — simulate by writing state in one test function and reading in
  another without calling commit (validates FR-008 persistence contract)

## Final Phase: Polish & Cross-Cutting

- [ ] T013 Update `.github/copilot-instructions.md` — add state keys documentation under "Git Workflow Actions" section: `commit_message_title`, `git.last_commit_title`, `git.last_commit_message`,
  `git.last_commit_body`, and document `git.last_commit_message` fallback behavior (NFR-004)
- [ ] T014 [US1] Run `python scripts/validate_test_structure.py` to verify 1:1:1 test structure compliance for all new test files
- [ ] T015 [US1] Run full test suite (`agdt-test` + `agdt-task-wait`) and verify zero regressions (SC-004)
- [ ] T016 [US1] Run `bash scripts/targeted-checks.sh` to verify lint, format, mypy, and per-file coverage pass (SC-002, NFR-003)

## Dependency Graph

```text
T001 → T002 → T004 → T006 → T007 → T008
T001 → T003 (parallel with T004)
T004 → T005 (parallel with T006)
T006 → T010, T011, T012
T008 → T009
T012 → T013 → T014 → T015 → T016
```

## FR Traceability Matrix

| FR | Tasks |
| --- | --- |
| FR-001 (title persistence + fallback) | T002, T004, T006, T007, T008 |
| FR-002 (full message persistence) | T004, T008, T010 |
| FR-003 (body persistence) | T002, T003, T004, T005, T010 |
| FR-004 (no update on failure) | T006, T008 |
| FR-005 (no update on dry-run) | T006, T008 |
| FR-006 (overwrite on each success) | T004, T005, T010, T011 |
| FR-007 (atomic all-or-nothing write) | T004, T005 |
| FR-008 (readable via agdt-get) | T005, T008, T012 |
| FR-009 (output-only, no intent signal) | T006, T009 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
