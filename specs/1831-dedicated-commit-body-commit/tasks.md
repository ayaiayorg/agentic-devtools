# Tasks: Dedicated commit-body.md for Commit Body

## Phase Mapping: Plan → Tasks

| Tasks Phase | Plan Phase(s) | Description |
|---|---|---|
| Phase 1: Setup | — | Project scaffolding (no direct plan equivalent) |
| Phase 2: Foundational | Plan Phase 1: Core Module | Core helper functions via TDD |
| Phase 3: User Story 2 (Show Command) | Plan Phase 2: Show Command | `agdt-commit-body-show` implementation |
| Phase 4: User Story 1 (Body Injection) | Plan Phase 3: Integration | Commit body injection into `commit_cmd()` |
| Phase 5: User Story 3 (Frontmatter) | Plan Phase 1: Core Module | YAML frontmatter parsing tests and verification |
| Phase 6: User Story 4 (Worktree Isolation) | Plan Phase 1: Core Module | Worktree isolation verification tests |
| Phase 7: Polish & Cross-Cutting | Plan Phase 4–5: Docs + Validation | Documentation updates and CI validation |

## Phase 1: Setup — Project Scaffolding

- [ ] T001 [US1] Create `tests/unit/cli/git/commit_body/__init__.py` and all parent `__init__.py` files
- [ ] T002 Create source module file `agentic_devtools/cli/git/commit_body.py` with imports and `CommitBodyResult` dataclass skeleton
- [ ] T003 Register `agdt-commit-body-show` entry point in `pyproject.toml` under `[project.scripts]`
- [ ] T004 Add `"agdt-commit-body-show"` to `COMMAND_MAP` in `agentic_devtools/cli/runner.py`

## Phase 2: Foundational — Core Helper Functions (TDD)

- [ ] T005 Write failing tests for `get_commit_body_path()` in `tests/unit/cli/git/commit_body/test_get_commit_body_path.py` — verifies path resolves to `{state_dir}/files/commit-body.md` (FR-005,
  FR-006)
- [ ] T006 Implement `get_commit_body_path()` in `agentic_devtools/cli/git/commit_body.py` (FR-005, FR-006)
- [ ] T007 [P] Write failing tests for `extract_title()` in `tests/unit/cli/git/commit_body/test_extract_title.py` — single line, multiline (only first line returned, rest discarded per FR-001)
- [ ] T008 [P] Write failing tests for `assemble_message()` in `tests/unit/cli/git/commit_body/test_assemble_message.py` — title + blank line + body (FR-001)
- [ ] T009 [P] Implement `extract_title()` in `agentic_devtools/cli/git/commit_body.py`
- [ ] T010 [P] Implement `assemble_message()` in `agentic_devtools/cli/git/commit_body.py`
- [ ] T011 Write failing tests for `parse_frontmatter()` in `tests/unit/cli/git/commit_body/test_parse_frontmatter.py` — no frontmatter, valid YAML, malformed YAML (FR-007), `None` result treated as
  `{}`, non-dict treated as malformed (FR-004), BOM before opening `---`
- [ ] T012 Implement `parse_frontmatter()` using `yaml.safe_load` (FR-004, FR-007) in `agentic_devtools/cli/git/commit_body.py`
- [ ] T013 Write failing tests for `read_commit_body()` in
  `tests/unit/cli/git/commit_body/test_read_commit_body.py` — file missing, empty,
  whitespace-only (FR-002), valid content happy path, >100KB hard limit
  (FR-011), non-UTF-8 error (FR-008), BOM stripping, parent `files/` dir missing (FR-006)
- [ ] T014 Implement `read_commit_body()` with MAX_BODY_FILE_SIZE=102400 enforcement, UTF-8 decoding, and BOM stripping in `agentic_devtools/cli/git/commit_body.py`

## Phase 3: User Story 2 — Show Command (P1)

- [ ] T015 [US2] Write failing tests for `show_cmd()` in
  `tests/unit/cli/git/commit_body/test_show_cmd.py` — file present with/without frontmatter
  happy path (FR-009), file missing (stderr + exit 1 per FR-003),
  file >100KB (stderr + exit 1 per FR-011), malformed YAML (warning + body only per FR-007)
- [ ] T016 [US2] Implement `show_cmd()` in `agentic_devtools/cli/git/commit_body.py` — prints path, character length, frontmatter detection status, parsed frontmatter section, and body content to
  stdout (FR-003, FR-009)
- [ ] T017 [US2] Export `show_cmd` from `agentic_devtools/cli/git/__init__.py`

## Phase 4: User Story 1 — Commit Body Injection (P1)

- [ ] T018 [US1] Write failing tests for body injection in `tests/unit/cli/git/commands/test_commit_cmd.py` — body present injects after title happy path (FR-001), missing body uses full `commit_message`
  unchanged (FR-002), empty/whitespace body treated as absent (FR-002), >100KB aborts commit (FR-011), multiline `commit_message` with file body discards inline body (FR-001)
- [ ] T019 [US1] Modify `commit_cmd()` in `agentic_devtools/cli/git/commands.py` to call `read_commit_body()`, `extract_title()`, and `assemble_message()` — integrating body injection after getting
  commit message (FR-001, FR-002)
- [ ] T020 [US1] Verify all existing `agdt-git-save-work` tests pass unchanged (SC-001 backward compatibility)

## Phase 5: User Story 3 — YAML Frontmatter Parsing (P2)

- [ ] T021 [US3] Write tests in `tests/unit/cli/git/commit_body/test_parse_frontmatter.py` for typed value extraction — list of integers, strings, nested dicts (FR-004), verifying frontmatter is
  excluded from body text injected into git message
- [ ] T022 [US3] Write test that `commit_cmd()` excludes frontmatter from final git commit message body — only body text after closing `---` is injected (FR-004)
- [ ] T023 [US3] Verify `show_cmd()` displays parsed frontmatter keys/values in a separate section when present (FR-009)

## Phase 6: User Story 4 — Worktree Isolation (P2)

- [ ] T024 [US4] Write tests in `tests/unit/cli/git/commit_body/test_get_commit_body_path.py` verifying path uses per-worktree state directory (FR-005) — two different worktree keys produce different
  paths
- [ ] T025 [US4] Write test that `read_commit_body()` in one worktree context never reads another worktree's file (FR-005)
- [ ] T026 [US4] Write test that missing `files/` subdirectory is treated as absent body without error (FR-006)

## Phase 7: Polish & Cross-Cutting

- [ ] T027 Add `commit-body.md` documentation section to `.github/copilot-instructions.md` describing file location, consumption by `agdt-git-save-work`, and title/body
  separation (FR-010)
- [ ] T028 Add `agdt-commit-body-show` to the CLI command tables in `.github/copilot-instructions.md` (FR-010)
- [ ] T029 Update "Initial Git Commit & Publish" workflow example in `.github/copilot-instructions.md` to reference `commit-body.md` as canonical body source (FR-010)
- [ ] T030 Add module-level docstring to `agentic_devtools/cli/git/commit_body.py` describing purpose, file format, and constants
- [ ] T031 [US1] Run `python scripts/validate_test_structure.py` — confirm 1:1:1 compliance for all new test files
- [ ] T032 [US1] Run `agdt-test` full suite — verify all tests pass with 100% branch coverage on new files (NFR-003, SC-003)
- [ ] T033 Run `bash scripts/targeted-checks.sh` — ruff, mypy, markdownlint pass
- [ ] T034 [US2] Smoke test `agdt-commit-body-show` end-to-end — create file, run command, verify happy-path output format (SC-002, FR-010)

## Task Dependencies

```text
T001 → T002 → T005, T006
T003, T004 → T016 (entry point registration before show command works)
T006 → T013, T014 (path helper needed by read)
T007, T008 → T009, T010 (tests before impl)
T011 → T012 (tests before impl)
T013 → T014 (tests before impl)
T014 → T015, T016 (read_commit_body needed by show)
T009, T010, T014 → T018, T019 (helpers needed for integration)
T019 → T020 (backward compat verified after integration)
T012 → T021, T022 (frontmatter impl needed)
T006 → T024, T025, T026 (path helper needed)
T020 → T031, T032, T033 (all tests pass before validation)
```

---
*Generated by Copilot SDK (claude-opus-4.6)*
