# Tasks: Issue Type Config in project.json (#1833)

## Phase Mapping: Plan → Tasks

This task breakdown is 1:1 aligned with the implementation phases in `plan.md`.

## Phase 1: Setup — Scaffolding & Directory Structure

- [ ] T001 Create new module file `agentic_devtools/cli/config/commit_type_resolution.py` with module docstring and initial imports
- [ ] T002 Scaffold pytest package directory for `commit_type_resolution` with `__init__.py`

## Phase 2: Foundational — Constants and Escape Helper

- [ ] T003 [P] Write tests for `STANDARD_COMMIT_TYPES` constant in `tests/unit/cli/config/commit_type_resolution/test_standard_commit_types.py` — verify it equals the 11 Conventional Commits types per
  FR-002
- [ ] T004 [P] Write tests for `_escape_single_quote()` in `tests/unit/cli/config/commit_type_resolution/test__escape_single_quote.py` — covers backslash-then-quote escaping per FR-004
- [ ] T005 Implement `STANDARD_COMMIT_TYPES` constant and `_MAX_DISPLAYED_TYPES = 20` in `agentic_devtools/cli/config/commit_type_resolution.py` (FR-002: full standard list)
- [ ] T006 Implement `_escape_single_quote(value: str) -> str` in `agentic_devtools/cli/config/commit_type_resolution.py` (FR-004: escape order `\` then `'`)

## Phase 3: User Story 1 — Default Issue Type Fallback (P1)

- [ ] T007 [US1] Write tests for `read_default_commit_type()` in `tests/unit/cli/config/commit_type_resolution/test_read_default_commit_type.py`
  — covers happy-path resolution: camelCase precedence over snake_case alias
  (FR-001), empty string ignored, non-string warning (FR-006)
- [ ] T008 [US1] Implement `read_default_commit_type(project_config: dict) -> tuple[str | None, str | None]`
  in `agentic_devtools/cli/config/commit_type_resolution.py` — reads `defaultCommitIssueType` with
  `default_commit_issue_type` alias (FR-001), handles malformed values (FR-006)
- [ ] T009 [US1] FR-003 Write tests for `resolve_commit_issue_type()` in
  `tests/unit/cli/config/commit_type_resolution/test_resolve_commit_issue_type.py` — covers: happy-path scenarios
  (explicit override wins, config default used, hardcoded "feat" fallback) (FR-003), `project_config=None`
  triggers `load_project_config()` (FR-003), misconfigured default warning (FR-005), no duplicate
  warnings, at least 8 scenarios per SC-004
- [ ] T010 [US1] Implement `resolve_commit_issue_type(explicit_type, *, project_config) -> tuple[str, list[str]]` in `agentic_devtools/cli/config/commit_type_resolution.py` — full resolution chain per
  FR-003, misconfiguration detection per FR-005

## Phase 4: User Story 2 — Validation Against Allowed Types (P2)

- [ ] T011 [US2] Write tests for `read_available_commit_types()` in `tests/unit/cli/config/commit_type_resolution/test_read_available_commit_types.py` — covers camelCase precedence over snake_case
  alias (FR-002), empty array falls back to standard list, non-array warning (FR-006), array with non-string elements warning (FR-006)
- [ ] T012 [US2] Implement `read_available_commit_types(project_config: dict) -> tuple[list[str], str | None]` in `agentic_devtools/cli/config/commit_type_resolution.py` — reads
  `availableCommitIssueTypes` with alias (FR-002), handles malformed values (FR-006)
- [ ] T013 [US2] Write tests for `validate_commit_issue_type()` in `tests/unit/cli/config/commit_type_resolution/test_validate_commit_issue_type.py` — covers:
  happy-path: valid type returns None (FR-004), invalid type returns warning string (FR-004), case-sensitive comparison,
  truncation at >20 entries with `'and N more'` (FR-004), single-quote escaping in type and list entries (FR-004)
- [ ] T014 [US2] Add `validate_commit_issue_type(issue_type: str, allowed_types: list[str]) -> str | None` to `agentic_devtools/cli/config/commit_type_resolution.py` — format per FR-004 with
  truncation and escaping
- [ ] T015 [US2] Extend `resolve_commit_issue_type()` to call the type-checking function (FR-004) and append any returned warnings to the result list (FR-003)

## Phase 5: User Story 3 — Configuration Discovery & Setup (P3)

- [ ] T016 [US3] Write tests for `agdt-setup` per-field idempotency in the project-config test file — covers: fresh config gets both fields
  (FR-007), existing camelCase preserved, existing snake_case alias
  preserved, mixed scenario only missing field added (FR-007)
- [ ] T017 [US3] Update `_prompt_project_config()` in `agentic_devtools/cli/setup/commands.py` to write `defaultCommitIssueType` and `availableCommitIssueTypes` defaults per FR-007 idempotency rules
  (camelCase canonical keys written only when both camelCase and snake_case alias absent)
- [ ] T018 [US3] Update module exports in `agentic_devtools/cli/config/__init__.py` (FR-007) — re-export `STANDARD_COMMIT_TYPES`, `resolve_commit_issue_type`, and the type-checking function
- [ ] T019 [US3] Wire `--commit-message-type` CLI arg in `agentic_devtools/cli/git/commands.py` to set `versionControl.commitMessageType` in state before commit message resolution
- [ ] T020 [US3] Write tests for `--commit-message-type` CLI arg mapping to `versionControl.commitMessageType` state in git command tests (FR-003)

## Phase 6: Polish & Cross-Cutting

- [ ] T021 [P] Update `.github/copilot-instructions.md` project config section — document `defaultCommitIssueType`, `availableCommitIssueTypes` fields, resolution priority, and validation behavior
  (SC-005)
- [ ] T022 [P] Update `agdt-setup` help text or prompt output in `agentic_devtools/cli/setup/commands.py` to describe commit type config fields and defaults (SC-005)
- [ ] T023 Execute full suite with `agdt-test` + `agdt-task-wait` to confirm zero regressions and 100% branch coverage on new module (SC-001)
- [ ] T024 Run `bash scripts/targeted-checks.sh` to confirm lint, format, type checking, and per-file coverage pass (SC-001)
- [ ] T025 [US3] Run `python scripts/validate_test_structure.py` to confirm 1:1:1 test structure compliance

## Task Dependencies

| Task | Depends On |
|------|-----------|
| T003–T004 | T001, T002 |
| T005–T006 | T003–T004 (TDD: tests first) |
| T007 | T005, T006 |
| T008 | T007 (TDD) |
| T009 | T008 |
| T010 | T009 (TDD) |
| T011 | T005, T006 |
| T012 | T011 (TDD) |
| T013 | T005, T006 |
| T014 | T013 (TDD) |
| T015 | T010, T014 |
| T016 | T005 |
| T017 | T016 (TDD), T018 |
| T018 | T010, T014 |
| T019 | T010 |
| T020 | T019 |
| T021–T022 | T017 |
| T023–T025 | All implementation tasks |

---
*Generated by Copilot SDK (claude-opus-4.6)*
