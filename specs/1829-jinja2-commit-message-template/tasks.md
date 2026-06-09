# Tasks: Jinja2 Commit Message Template System

## Phase Mapping: Plan → Tasks

| Tasks Phase | Plan Phase(s) | Description |
|---|---|---|
| Phase 1: Setup — Project Scaffolding | Phase 1: Template Rendering Core, Phase 2: Setup Integration | Shared scaffolding needed before rendering and setup work |
| Phase 2: Foundational — Non-Existent Repo Resolution | Phase 1: Template Rendering Core | Foundational helper for template rendering |
| Phase 3: User Story 1 — Default Template Auto-Creation on Setup | Phase 2: Setup Integration | Setup creation/validation and setup command integration |
| Phase 4: User Story 2 — Commit Message Rendering from Template | Phase 1: Template Rendering Core | Core template rendering implementation and command integration |
| Phase 5: User Story 3 — Warning on Unresolved Template Variables | Phase 1: Template Rendering Core | Unresolved variable warning behavior |
| Phase 6: User Story 4 — Template Validation During Setup | Phase 2: Setup Integration | Setup-time validation behavior and integration tests |
| Phase 7: User Story 5 — Fallback to Raw Commit Message | Phase 1: Template Rendering Core | Backward-compatible fallback behavior |
| Phase 8: Edge Cases & Hardening | Phase 4: Edge Cases & Hardening | Hardening and edge-case protections |
| Phase 9: Polish & Cross-Cutting — Documentation & Final Validation | Phase 3: Documentation | Documentation updates and final verification tasks |

## Phase 1: Setup — Project Scaffolding

- [ ] T001 Create module file `agentic_devtools/cli/git/commit_template.py` with module docstring, constants `TEMPLATE_PATH`, `REQUIRED_VARIABLES`, and `DEFAULT_JIRA_TYPE_MAPPING`
- [ ] T002 Create module file `agentic_devtools/cli/setup/commit_template_setup.py` with module docstring and `DEFAULT_TEMPLATE` constant (FR-001 template content)
- [ ] T003 [US2] Create test directory structure `tests/unit/cli/git/commit_template/` with `__init__.py`
- [ ] T004 [US1] Create test directory structure `tests/unit/cli/setup/commit_template_setup/` with `__init__.py`
- [ ] T005 [US2] Create test directory `tests/unit/cli/github/repo_resolution/` with `__init__.py` (if not existing)

## Phase 2: Foundational — Non-Existent Repo Resolution

- [ ] T006 [US2] Implement `resolve_github_repo_safe() -> str | None` in `agentic_devtools/cli/github/repo_resolution.py` using `_resolve_repo_from_git_remote()` and `_validate_repo_format()` without
  calling `sys.exit(1)`
- [ ] T007 [US2] Write tests for `resolve_github_repo_safe()` in `tests/unit/cli/github/repo_resolution/test_resolve_github_repo_safe.py` covering FR-003 success, missing remote, malformed repo,
  and `github.repo` state fallback

## Phase 3: User Story 1 — Default Template Auto-Creation on Setup (P1)

- [ ] T008 [US1] Write tests for `ensure_commit_template()` in `tests/unit/cli/setup/commit_template_setup/test_ensure_commit_template.py` — covers FR-001 happy-path default template creation,
  FR-002 (does not
  overwrite existing), FR-008 (creates `.agdt/config/` directory)
- [ ] T009 [US1] Implement `ensure_commit_template(git_root: Path) -> bool` in `agentic_devtools/cli/setup/commit_template_setup.py` — creates template if missing (FR-001), skips if exists (FR-002),
  creates directory structure (FR-008)
- [ ] T010 [US1] Write tests for `validate_commit_template()` in `tests/unit/cli/setup/commit_template_setup/test_validate_commit_template.py` — covers FR-006 (validates required variables present,
  warns on missing, allows extra variables)
- [ ] T011 [US1] Implement `validate_commit_template(git_root: Path) -> list[str]` in `agentic_devtools/cli/setup/commit_template_setup.py` using Jinja2 AST/meta parsing (FR-006)
- [ ] T012 [US1] Integrate `ensure_commit_template()` and `validate_commit_template()` into `_run_file_modifying_steps()` in `agentic_devtools/cli/setup/commands.py` gated by `--skip-templates` and
  `skip_repo_steps` (FR-001, FR-006)
- [ ] T013 [US1] Update `--skip-templates` help text in `agentic_devtools/cli/setup/commands.py` to mention commit template creation/validation is also skipped (FR-009 partial)

## Phase 4: User Story 2 — Commit Message Rendering from Template (P1)

- [ ] T014 [US2] Write tests for `_resolve_issue_key()` in `tests/unit/cli/git/commit_template/test__resolve_issue_key.py` — covers FR-003 resolution chain and normalization rules (int, digits-only
  string, `#N` pattern, Jira-style keys, leading zeros)
- [ ] T015 [US2] Implement `_resolve_issue_key() -> tuple[str | None, Any]` in `agentic_devtools/cli/git/commit_template.py` per FR-003 normalization decision tree
- [ ] T016 [P] [US2] Write tests for `_resolve_issue_link()` in `tests/unit/cli/git/commit_template/test__resolve_issue_link.py` — covers FR-003 derivation from resolved repo + numeric issue,
  unresolved when repo fails or Jira-style key
- [ ] T017 [P] [US2] Write tests for `_resolve_issue_type()` in `tests/unit/cli/git/commit_template/test__resolve_issue_type.py` — covers FR-003 `versionControl.commitMessageType` priority and Jira
  type mapping
- [ ] T018 [P] [US2] Write tests for `_resolve_commit_title()` in `tests/unit/cli/git/commit_template/test__resolve_commit_title.py` — covers FR-003 `versionControl.commitMessageTitle` resolution
- [ ] T019 [P] [US2] Write tests for `_resolve_commit_body()` in `tests/unit/cli/git/commit_template/test__resolve_commit_body.py` — covers FR-003 file reading, absolute/relative path resolution,
  missing file → unresolved
- [ ] T020 [US2] Implement `_resolve_issue_link(normalized_key, raw_key, git_root)` using `resolve_github_repo_safe()` per FR-003
- [ ] T021 [US2] Implement `_resolve_issue_type() -> str | None` with `DEFAULT_JIRA_TYPE_MAPPING` per FR-003
- [ ] T022 [US2] Implement `_resolve_commit_title() -> str | None` per FR-003
- [ ] T023 [US2] Implement `_resolve_commit_body(git_root: Path) -> str | None` with path resolution per FR-003
- [ ] T024 [US2] Write tests for `_build_render_context()` in `tests/unit/cli/git/commit_template/test__build_render_context.py` — covers full context assembly per FR-003
- [ ] T025 [US2] Implement `_build_render_context(git_root: Path) -> dict[str, str]` composing all resolver functions per FR-003
- [ ] T026 [US2] Write tests for `_load_template()` in `tests/unit/cli/git/commit_template/test__load_template.py` — covers valid file, empty file (FR-007), whitespace-only file (FR-007), syntax
  errors (FR-007), missing file (FR-005)
- [ ] T027 [US2] Implement `_load_template(git_root: Path) -> str | None` with empty/whitespace detection and diagnostic warning (FR-007)
- [ ] T028 [US2] Write tests for `resolve_commit_message_from_template()` in `tests/unit/cli/git/commit_template/test_resolve_commit_message_from_template.py` — covers happy path, no template (FR-005
  fallback returns None), template syntax error (FR-007 fallback), CLI arg override priority
- [ ] T029 [US2] Implement `resolve_commit_message_from_template(git_root: Path | None) -> str | None` orchestrating load, build context, render, and warnings
- [ ] T030 [US2] Integrate `resolve_commit_message_from_template()` into `commit_cmd()` in `agentic_devtools/cli/git/commands.py` — insert between CLI arg check and `get_commit_message()` fallback
  (FR-005 backward compat preserved)
- [ ] T031 [US2] Update error message in `get_commit_message()` to mention template alternative when `commit_message` is also empty (FR-007 actionable error)

## Phase 5: User Story 3 — Warning on Unresolved Template Variables (P1)

- [ ] T032 [US3] Write tests for `_warn_unresolved_variables()` in `tests/unit/cli/git/commit_template/test__warn_unresolved_variables.py` — covers FR-004 happy-path (no warnings when all resolved)
  and edge-case behavior (one warning per unresolved variable, multiple unresolved listed individually, warnings emitted to stderr)
- [ ] T033 [US3] Implement `_warn_unresolved_variables(context, template_content)` using Jinja2 `meta.find_undeclared_variables()` to detect referenced-but-missing vars and emit `Warning:` prefixed
  messages to stderr (FR-004)

## Phase 6: User Story 4 — Template Validation During Setup (P2)

- [ ] T034 [US4] Add test cases to `tests/unit/cli/setup/commit_template_setup/test_validate_commit_template.py` for: all required present (no warning), missing `issueLink` (warning), extra custom
  variables (no error) — validates FR-006 behavior
- [ ] T035 [US4] Add integration test verifying `agdt-setup` prints validation warnings for malformed template but completes successfully (FR-006 non-blocking validation), and verify `--help` output
  for `--skip-templates` mentions commit template creation/validation behavior (FR-009)

## Phase 7: User Story 5 — Fallback to Raw Commit Message (P2)

- [ ] T036 [US5] Add test cases to `test_resolve_commit_message_from_template.py` verifying: no template file → returns `None` triggering `commit_message` state fallback (FR-005); template exists but
  rendering fails → warning + returns `None` (FR-007); template + render fail + `commit_message` empty → actionable exit error (FR-007)
- [ ] T037 [US5] Add integration-level test in `tests/unit/cli/git/commit_template/test_resolve_commit_message_from_template.py` verifying `--commit-message` CLI arg bypasses template entirely (FR-003
  priority order)

## Phase 8: Edge Cases & Hardening (P2)

- [ ] T038 [P] [US5] Add edge case tests to `test__load_template.py`: zero-byte file emits "commit template file is empty or whitespace-only" warning (FR-007), `TemplateSyntaxError` emits Jinja2 error
  message in warning (FR-007)
- [ ] T039 [P] [US2] Add edge case tests to `test__resolve_commit_body.py`: permission error on body file → unresolved, path traversal attempt outside repo root → unresolved
- [ ] T040 [US2] Implement path traversal safety check in `_resolve_commit_body()` — validate resolved path is within git repo root
- [ ] T041 [US5] Implement final fallback error in `resolve_commit_message_from_template()`: when template fails AND caller's `get_commit_message()` also returns empty, emit actionable error
  instructing user to fix template or set `commit_message` (FR-007)

## Phase 9: Polish & Cross-Cutting — Documentation & Final Validation

- [ ] T042 Update `docs/state-keys.md` to document `versionControl.commitMessageType`, `versionControl.commitMessageTitle`, `versionControl.commitMessageBodyFile`, `issueManagement.issueLink`, and
  `issueManagement.issueKey` (FR-009)
- [ ] T043 Update `.github/copilot-instructions.md` with commit template section: feature overview, priority chain, variable resolution rules, troubleshooting (FR-009)
- [ ] T044 Add commit template documentation to `scripts/agentic_devtools/copilot-instructions.md` — how to use default template, customize, and troubleshoot (FR-009)
- [ ] T045 [US2] [US3] [US5] Run `agdt-test-file --source-file agentic_devtools/cli/git/commit_template.py` and verify 100% branch coverage
- [ ] T046 [US1] [US4] Run `agdt-test-file --source-file agentic_devtools/cli/setup/commit_template_setup.py` and verify 100% branch coverage
- [ ] T047 [US1] [US2] [US3] [US4] [US5] Run `python scripts/validate_test_structure.py` to confirm 1:1:1 test structure compliance
- [ ] T048 [US1] [US2] [US3] [US4] [US5] Run `bash scripts/targeted-checks.sh` to verify ruff, mypy, and markdownlint pass
- [ ] T049 [US1] [US2] [US3] [US4] [US5] Run `agdt-test` full suite and verify no regressions

## Dependency Graph

```text
T001-T005 (parallel scaffolding)
    │
    ├── T006 → T007
    │
    ├── T008 → T009 → T012
    ├── T010 → T011 → T012 → T013
    │
    ├── T014 → T015 ─┐
    ├── T016 ─────────┤
    ├── T017 ─────────┤
    ├── T018 ─────────┤
    ├── T019 ─────────┤
    │                  ▼
    │         T020-T023 (implementations, depend on T006/T007)
    │                  │
    │         T024 → T025
    │         T026 → T027
    │                  │
    │         T028 → T029 → T030 → T031
    │
    ├── T032 → T033 (depends on T029)
    ├── T034 → T035 (depends on T011)
    ├── T036 → T037 (depends on T029)
    ├── T038-T041 (depends on T027, T029)
    │
    └── T042-T049 (final phase, depends on all above)
```

## FR Traceability Matrix

| FR | Tasks |
|----|-------|
| FR-001 | T002, T008, T009, T012 |
| FR-002 | T008, T009 |
| FR-003 | T014–T025, T029, T030, T037, T039, T040 |
| FR-004 | T032, T033 |
| FR-005 | T026, T028, T030, T036 |
| FR-006 | T010, T011, T012, T034, T035 |
| FR-007 | T026, T027, T028, T029, T036, T038, T041 |
| FR-008 | T008, T009 |
| FR-009 | T013, T035, T042, T043, T044 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
