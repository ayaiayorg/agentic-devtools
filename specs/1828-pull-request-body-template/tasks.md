# Tasks: PR Body Template with Commit Aggregation Fallback

## Phase Mapping: Plan → Tasks

| Tasks Phase | Plan Phase(s) | Description |
| --- | --- | --- |
| Phase 1: Setup | Phase 4: Register CLI Entry Points | CLI scaffolding, runner wiring, and test-directory setup |
| Phase 2: Foundational | Phase 1: Shared Template Module | Shared git/template helper foundations |
| Phase 3: User Story 1 | Phase 1: Shared Template Module; Phase 3: Integrate Template into Azure DevOps | Core PR body resolution plus Azure DevOps consumption |
| Phase 4: User Story 2 | Phase 2: Persist Effective Commit Message in `agdt-git-save-work` | FR-008 state persistence for effective commit messages |
| Phase 5: User Story 3 | Phase 1: Shared Template Module; Phase 6: Default Template Content | Initial template creation and default template content |
| Phase 6: User Story 4 | Phase 1: Shared Template Module; Phase 3: Integrate Template into Azure DevOps | Missing-template fallback and validation behavior |
| Phase 7: User Story 5 | Phase 1: Shared Template Module | User-owned template customization persistence |
| Phase 8: GitHub PR Creation Integration | Phase 5: GitHub PR Creation Integration | GitHub-specific PR creation path using shared template logic |
| Final Phase: Polish & Cross-Cutting | Phases 1-6 | Validation, packaging, and documentation across all implementation work |

## Phase 1: Setup — Project Scaffolding

- [ ] T001 Create module file `agentic_devtools/cli/pr_template.py` with module docstring, imports, and constants (`DEFAULT_TEMPLATE_CONTENT`, `TEMPLATE_RELATIVE_PATH`); import
  `STATE_LAST_COMMIT_MESSAGE` from `agentic_devtools.cli.git.core` rather than redefining it
- [ ] T002 Add `STATE_LAST_COMMIT_MESSAGE = "git.last_commit_message"` constant to `agentic_devtools/cli/git/core.py`
- [ ] T003 [US1] Create test directory structure `tests/unit/cli/pr_template/` with `__init__.py` files at each level
- [ ] T004 [US1] Create test directory `tests/unit/cli/github/pr_create/` with `__init__.py` files
- [ ] T005 Register `agdt-init-pr-template` entry point in `pyproject.toml` under `[project.scripts]`
- [ ] T006 Register `agdt-gh-create-pull-request` entry point in `pyproject.toml` under `[project.scripts]`
- [ ] T007 Add `agdt-init-pr-template` to `COMMAND_MAP` in `agentic_devtools/cli/runner.py`
- [ ] T008 Add `agdt-gh-create-pull-request` to `COMMAND_MAP` in `agentic_devtools/cli/runner.py`

## Phase 2: Foundational — Shared Template Utilities

- [ ] T009 [FR-004] Write tests for `resolve_main_ref()` in `tests/unit/cli/pr_template/test_resolve_main_ref.py` — cover origin/main exists (happy path), only main exists, neither exists
- [ ] T010 Implement `resolve_main_ref() -> str | None` in `agentic_devtools/cli/pr_template.py` using `run_git("rev-parse", "--verify", ...)` with fallback from `origin/main` → `main` → `None`
- [ ] T011 [FR-003] Write tests for `get_template_path()` in `tests/unit/cli/pr_template/test_get_template_path.py` — cover git root resolution and path construction (happy path)
- [ ] T012 Implement `get_template_path(git_root: Path | None = None) -> Path` in `agentic_devtools/cli/pr_template.py` resolving via `git rev-parse --show-toplevel`

## Phase 3: User Story 1 — Standard PR Creation with Template (P1)

- [ ] T013 [US1] Write tests for `resolve_full_commit_message()` in `tests/unit/cli/pr_template/test_resolve_full_commit_message.py` — cover state hit (happy path, FR-004 step 1),
  single commit from git log, multi-commit aggregation with `---` separator (FR-005), empty branch, git failure fallback to literal
- [ ] T014 [US1] Implement `resolve_full_commit_message() -> str` in `agentic_devtools/cli/pr_template.py` (FR-004): check state `git.last_commit_message`, then `git log --format=%B%x1e {ref}..HEAD`
  with `\x1e` delimiter parsing, then literal fallback; join multiple commits with `\n\n---\n\n` (FR-005); handle empty bodies without excessive separators
- [ ] T015 [US1] Write tests for `resolve_pr_body()` in `tests/unit/cli/pr_template/test_resolve_pr_body.py` — cover template present with placeholder (happy path, FR-003),
  template with markdown content preserved verbatim (FR-009), template without placeholder renders as-is (FR-007), empty template returns commit message (FR-007),
  missing template returns commit message with warning (FR-006)
- [ ] T016 [US1] Implement `resolve_pr_body() -> str` in `agentic_devtools/cli/pr_template.py` (FR-003, FR-006, FR-007, FR-009): load template, warn on missing, handle empty/whitespace, replace
  `{{fullCommitMessage}}` via `str.replace()`, return final body preserving all markdown content
- [ ] T017 [US1] [FR-003] Write tests for Azure DevOps `create_pull_request()` integration in `tests/unit/cli/azure_devops/commands/test_create_pull_request.py` — verify `resolve_pr_body()` is called
  and its output used as description
- [ ] T018 [US1] Modify `create_pull_request()` in `agentic_devtools/cli/azure_devops/commands.py` to call `resolve_pr_body()` for the description field (FR-003), replacing the current
  `get_value("description") or ""` pattern

## Phase 4: User Story 2 — Fallback to Git Log Aggregation (P1)

- [ ] T019 [US2] Write tests for `_persist_effective_commit_message()` in `tests/unit/cli/git/commands/test__persist_effective_commit_message.py` — cover FR-008 normal commit (happy path),
  amend, and dry-run skip paths
- [ ] T020 [US2] Implement `_persist_effective_commit_message(dry_run: bool) -> None` in `agentic_devtools/cli/git/commands.py` (FR-008): run `git log -1 --format=%B`, strip trailing whitespace, call
  `set_value(STATE_LAST_COMMIT_MESSAGE, message)` using the constant imported from `agentic_devtools.cli.git.core`
- [ ] T021 [US2] Integrate `_persist_effective_commit_message()` call into `save_work()` in `agentic_devtools/cli/git/commands.py` after commit/amend step but before push (FR-008)
- [ ] T022 [US2] Add integration-style tests verifying `save_work()` writes `git.last_commit_message` to state for FR-008 after both new commit and amend paths
- [ ] T023 [P] [US2] Add test cases to `test_resolve_full_commit_message.py` for multi-commit aggregation with subject-only commits (no excessive blank lines per FR-005 edge cases)

## Phase 5: User Story 3 — Initial Template Setup (P1)

- [ ] T024 [US3] Write tests for `init_pr_template()` in `tests/unit/cli/pr_template/test_init_pr_template.py` — cover creation when missing (happy path, FR-001), skip when exists (FR-002),
  directory creation, content validation including all checklist sections and `{{fullCommitMessage}}` placeholder
- [ ] T025 [US3] Implement `init_pr_template()` CLI entry point in `agentic_devtools/cli/pr_template.py` (FR-001, FR-002): check existence, create parent dirs, write `DEFAULT_TEMPLATE_CONTENT` with
  German-language operational checklist sections (Getestet, Database Schema Changes, Mgm-CLI Updates, Workbench Infrastruktur Updates, Infrastruktur Kommunikation, Dokumentation) and
  `{{fullCommitMessage}}` placeholder
- [ ] T026 [P] [US3] Add idempotency tests: run `init_pr_template()` multiple times, assert file unchanged on subsequent runs (FR-002 byte-for-byte preservation)

## Phase 6: User Story 4 — Template Validation at PR Creation Time (P2)

- [ ] T027 [US4] Write tests for missing-template warning path in `tests/unit/cli/pr_template/test_resolve_pr_body.py` — verify stderr warning output suggests `agdt-init-pr-template` (FR-006), PR
  still created with fallback body
- [ ] T028 [US4] Write tests for template-without-placeholder path — verify no error raised, template rendered as-is (FR-007)
- [ ] T029 [P] [US4] Write tests for empty (zero-byte) template — verify `resolve_full_commit_message()` result used as body (FR-007)

## Phase 7: User Story 5 — User Customization Persistence (P2)

- [ ] T030 [US5] Write tests verifying `init_pr_template()` does NOT overwrite existing customized template (FR-002) — modify content, run init, assert content unchanged
- [ ] T031 [P] [US5] Write tests verifying `resolve_pr_body()` respects relocated `{{fullCommitMessage}}` placeholder in user-customized template (FR-009, FR-003)
- [ ] T032 [P] [US5] Write tests verifying commit messages with markdown special characters (backticks, pipes, brackets) are preserved verbatim in interpolation (FR-009)

## Phase 8: GitHub PR Creation Integration (P1)

- [ ] T033 [US1] [FR-003] Write tests for `create_pull_request()` in `tests/unit/cli/github/pr_create/test_create_pull_request.py` — cover resolved template body passed to `gh pr create --body`,
  missing-template fallback, CLI argument construction
- [ ] T034 [US1] Create `agentic_devtools/cli/github/pr_create.py` with `create_pull_request()` implementation using `gh pr create` and `resolve_pr_body()` (FR-003)
- [ ] T035 [US1] Add async wrapper and CLI entry point function in `agentic_devtools/cli/github/pr_create.py` for background task execution
- [ ] T036 [US1] Export new command from `agentic_devtools/cli/github/__init__.py`

## Final Phase: Polish & Cross-Cutting

- [ ] T037 [US1] [US3] Reinstall package with `pip install -e .` and verify both `agdt-init-pr-template` and `agdt-gh-create-pull-request` commands are available
- [ ] T038 [US1] Run `python scripts/validate_test_structure.py` to confirm 1:1:1 test structure compliance
- [ ] T039 Run `ruff check --fix . && ruff format .` to ensure lint/format compliance
- [ ] T040 [US1] Run `agdt-test` full suite to verify no regressions and 100% branch coverage on new modules
- [ ] T041 Update `scripts/agentic_devtools/copilot-instructions.md` to document `agdt-init-pr-template` and `agdt-gh-create-pull-request` commands

## Dependency Graph

```text
T001 ← T009, T010, T011, T012, T013, T014, T015, T016
T002 ← T019, T020
T003 ← T009, T011, T013, T015, T024, T027
T004 ← T033
T005, T007 ← T025 (CLI registration needed for entry point)
T006, T008 ← T034 (CLI registration needed for entry point)
T010 ← T014 (resolve_main_ref used by resolve_full_commit_message)
T012 ← T016 (get_template_path used by resolve_pr_body)
T014 ← T016 (resolve_full_commit_message used by resolve_pr_body)
T016 ← T018 (resolve_pr_body used by Azure DevOps integration)
T016 ← T034 (resolve_pr_body used by GitHub integration)
T020 ← T021 (helper must exist before integration call)
T025 ← T030 (init must work before testing non-overwrite)
T037 ← T038, T039, T040 (install before final validation)
```

## FR Traceability Matrix

| FR | Primary Tasks |
| --- | --- |
| FR-001 | T024, T025 |
| FR-002 | T024, T025, T026, T030 |
| FR-003 | T015, T016, T017, T018, T031, T033, T034 |
| FR-004 | T013, T014 |
| FR-005 | T014, T023 |
| FR-006 | T015, T016, T027 |
| FR-007 | T015, T016, T028, T029 |
| FR-008 | T019, T020, T021, T022 |
| FR-009 | T015, T016, T031, T032 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
