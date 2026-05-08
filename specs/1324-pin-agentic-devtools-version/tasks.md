# Tasks: Pin agentic-devtools Version & Guard agdt-setup

**Issue**: [#1324](https://github.com/ayaiayorg/agentic-devtools/issues/1324)

## Phase 1: Setup — Project Scaffolding

- [ ] T001 Add `"packaging>=21.0"` to `[project.dependencies]` in `pyproject.toml` and run `pip install -e .` to confirm resolution
- [ ] T002 Create directory `agentic_devtools/cli/setup/` with `__init__.py` if it does not already exist
- [ ] T003 Create directory `tests/unit/cli/setup/version_guard/` with `__init__.py` files at each level
- [ ] T004 [P] Create directory `tests/unit/cli/setup/gitignore_negations/` with `__init__.py` files at each level

## Phase 2: Foundational — Version Comparison & Gitignore Helpers

- [ ] T005 Write tests `tests/unit/cli/setup/version_guard/test__fallback_compare.py` covering: happy-path (equal versions, older/newer), pre-release suffixes (`dev`, `alpha`, `rc`, `post`), local metadata
  stripping (`+local`), non-numeric segments, empty strings, garbage input fail-open — 100% coverage of `_fallback_compare`
- [ ] T006 Create `agentic_devtools/cli/setup/version_guard.py` with `_fallback_compare(running: str, pinned: str) -> int` implementing NFR-003 segment-based fallback (strip `+local`, split on `.`,
  decompose segments with suffix ordering, pad, compare lexicographically, fail-open on error)
- [ ] T007 Write tests `tests/unit/cli/setup/version_guard/test_compare_versions.py` covering: happy-path (PEP 440 normal versions, equal versions), pre-release ordering (`0.2.69.dev1` < `0.2.69`), post-release,
  fallback path when `packaging` import fails (mock `ImportError`)
- [ ] T008 Add `compare_versions(running: str, pinned: str) -> int` to `version_guard.py` using `packaging.version.Version` with try/except fallback to `_fallback_compare`; log warning on fallback
- [ ] T009 Write tests `tests/unit/cli/setup/version_guard/test_check_version_guard.py` covering: happy-path (equal version → `None`, newer version → `None`),
  no `project.json` → `None` (FR-010), no `agdt_version` key → `None` (FR-010), malformed `agdt_version`
  (empty, garbage) → `None` + warning logged (FR-011), older + no force → `"block"` + stderr contains running version, required version, upgrade command, `--force-old-version` (FR-005), older + force
  → `"force"` + warning on stderr (FR-009), force + equal/newer → `None` silently (US3/AS4)
- [ ] T010 Add `check_version_guard(git_root: Path | None, force_old_version: bool) -> str | None` to `version_guard.py` implementing:
  load `project.json` via `load_project_config`, read `agdt_version`, handle missing/None/malformed values (FR-010, FR-011),
  compare versions, return `None`/`"block"`/`"force"`, emit error to stderr on block (FR-005),
  emit warning to stderr on force (FR-009), silently return `None` when force + version >= pinned (US3/AS4)
- [ ] T011 [P] Write tests `tests/unit/cli/setup/gitignore_negations/test_ensure_root_gitignore_negations.py` covering:
  happy-path (insert after `.agdt/` rule), idempotent (already present), no `.gitignore` file,
  `.gitignore` exists but no `.agdt/` rule, partial negation rules already present, file permissions error
- [ ] T012 [P] Create `agentic_devtools/cli/setup/gitignore_negations.py` with `ensure_root_gitignore_negations(git_root: Path) -> bool` implementing FR-013: read root `.gitignore`, find `.agdt/`
  line, insert `!.agdt/`, `!.agdt/config/`, `!.agdt/config/project.json` after it in order, idempotent, handle missing file / no `.agdt/` rule / not writable
- [ ] T013 [P] Write integration test `tests/unit/cli/setup/gitignore_negations/test_ensure_root_gitignore_negations_integration.py` that initializes a temp git repo, writes `.gitignore` with
  `.agdt/`, runs helper, shells out to `git check-ignore .agdt/config/project.json` to confirm file is NOT ignored

## Phase 3: User Story 1 — Version Pinning on Successful Setup (P1)

- [ ] T014 [US1] Modify `agentic_devtools/cli/setup/commands.py` → `setup_cmd()` to: (a) move `git_root = _get_git_repo_root()` immediately after argparse, (b) add `--force-old-version` argparse flag
  (`store_true`), (c) insert version guard call after `git_root` — if `"block"` then `sys.exit(1)` before any local-only steps, if `"force"` set `skip_repo_steps=True`, (d) gate local-only steps to
  NOT run when guard returns `"block"` (FR-004 fail-fast), (e) gate `_run_file_modifying_steps()` and PR workflow to NOT run when `skip_repo_steps=True`, (f) inside `_run_file_modifying_steps()` add
  `ensure_root_gitignore_negations(git_root)` call after `ensure_agdt_gitignore()` (FR-013), (g) as LAST step inside `_run_file_modifying_steps()` write `agdt_version` to `project.json` via
  `load_project_config`/`save_project_config` (FR-001, FR-002, FR-012), (h) remove/update any outdated console guidance about manually adding `!.agdt/.gitignore` negation rules
- [ ] T015 [US1] Write/update tests in `tests/unit/cli/setup/commands/` for version pin write:
  happy-path (mock `_run_file_modifying_steps` internals to verify `agdt_version` is written as LAST step), verify
  existing keys preserved (FR-012), verify version string matches `__version__` (FR-002), verify no write when preceding step fails, verify idempotent on same version (US1/AS3), verify update on newer
  version (US1/AS2)
- [ ] T016 [US1] Write/update tests in `tests/unit/cli/setup/commands/` for gitignore negation integration: verify `ensure_root_gitignore_negations()` is called inside `_run_file_modifying_steps()`
  after `ensure_agdt_gitignore()`, verify not called when `skip_repo_steps=True`

## Phase 4: User Story 2 — Block Downgrade on Older Version (P1)

- [ ] T017 [US2] Write/update tests in `tests/unit/cli/setup/commands/` for fail-fast block path:
  happy-path (mock `check_version_guard` → `None`, assert normal execution),
  negative (mock `check_version_guard` → `"block"`, assert `sys.exit(1)`, assert `_run_file_modifying_steps` NOT
  called, assert local-only steps (cert prefetch, managed installs, dependency check, env persist) NOT called (FR-004),
  assert `agdt_version` NOT modified, assert no branch created, no PR opened)
- [ ] T018 [US2] Write/update tests for happy-path pass-through when no `agdt_version` exists:
  mock `check_version_guard` → `None`, assert both local-only and `_run_file_modifying_steps()` run normally (FR-010)
- [ ] T019 [US2] Write/update test verifying `_get_git_repo_root()` is called BEFORE `check_version_guard()` via mock call-order assertion (NFR-001)

## Phase 5: User Story 3 — Force Override for Local-Only Steps (P2)

- [ ] T020 [US3] Write/update tests in `tests/unit/cli/setup/commands/` for happy-path force-skip path:
  mock `check_version_guard` → `"force"`, assert exit code 0, assert local-only steps ARE called, assert
  `_run_file_modifying_steps()` NOT called, assert PR workflow NOT invoked, assert `agdt_version` NOT modified (FR-008)
- [ ] T021 [US3] Write/update tests for flag interaction `--force-old-version` + `--skip-pr-workflow`: assert both flags respected independently, PR workflow not invoked, repo-modifying steps skipped
- [ ] T022 [US3] Write/update tests for flag interaction `--force-old-version` + `--system-only`: assert `--system-only` behavior preserved, repo-modifying steps still skipped by force flag

## Phase 6: User Story 4 — Clear Version Mismatch Messaging (P2)

- [ ] T023 [US4] Write/update tests verifying error message content on block path:
  happy-path (stderr contains exact running version, exact required version, `python setup-dev-tools.py`,
  `--force-old-version`) (FR-005)
- [ ] T024 [US4] Write/update tests verifying warning message content on happy-path force path: captured stderr explains repo files will not be modified and mode is not recommended (FR-009)

## Phase 7: Polish & Cross-Cutting

- [ ] T025 Run `python scripts/validate_test_structure.py` and fix any structural violations
- [ ] T026 Run `ruff check --fix . && ruff format .` to fix lint/format issues
- [ ] T027 Run `bash scripts/run-pr-checks.sh` — all checks must pass (SC-006)
- [ ] T028 Update `agentic_devtools/cli/setup/__init__.py` to export new public symbols (`check_version_guard`, `compare_versions`, `ensure_root_gitignore_negations`)

---

## Dependency Graph

```text
T001 ─┐
T002 ─┤
T003 ─┼→ T005 → T006 → T007 → T008 → T009 → T010 ─┐
T004 ─┼→ T011 → T012                                 │
      └→ T011 → T013                                 │
                                                      ├→ T014 → T015
                                                      │       → T016
                                                      │       → T017
                                                      │       → T018
                                                      │       → T019
                                                      │       → T020
                                                      │       → T021
                                                      │       → T022
                                                      │       → T023
                                                      │       → T024
                                                      │
T015–T024 ──────────────────────────→ T025 → T026 → T027
T014 ────────────────────────────────→ T028
```

## Requirement Traceability

| Requirement | Task(s) |
|---|---|
| FR-001 (version write on success) | T014(g), T015 |
| FR-002 (version as string from `__version__`) | T014(g), T015 |
| FR-003 (PEP 440 comparison) | T005, T006, T007, T008, T009, T010 |
| FR-004 (fail-fast, no local steps) | T014(c)(d), T017 |
| FR-005 (error message content) | T009, T010, T023 |
| FR-006 (equal/newer proceeds normally) | T009, T010, T014(g), T015 |
| FR-007 (force allows local-only) | T009, T014(e), T020 |
| FR-008 (force does not update version) | T014(e), T020 |
| FR-009 (force warning message) | T009, T010, T024 |
| FR-010 (no guard when no agdt_version) | T009, T010, T018 |
| FR-011 (malformed version warning) | T009, T010 |
| FR-012 (preserve existing keys) | T014(g), T015 |
| FR-013 (gitignore negation rules) | T011, T012, T013, T014(f), T016 |
| NFR-001 (guard before file-modifying) | T014(a)(c), T019 |
| NFR-002 (output style) | T009, T023, T024 |
| NFR-003 (packaging dep + fallback) | T001, T005, T006, T007, T008 |
| NFR-004 (100% coverage, 1:1:1) | T003, T004, T005, T007, T009, T011, T013, T015–T024, T025 |

## Remediation Notes

- **[F-01]** Resolved: The E.2 coverage data (`test-coverage.json`) has been updated to replace all stale task IDs (T029, T031, T032, T033, T039) from a prior draft
  with the correct task IDs from the current traceability table (T001–T028). All 13 FRs now reference valid, existing tasks. Additionally, FR-008 traceability was strengthened by adding T014(e) (the
  implementation sub-item that gates `_run_file_modifying_steps()`) alongside T020 (the test task).
- **[G-01]** Fixed: All five `setup_cmd()` modifications consolidated into single task T014 with sub-items (a–h).
- **[G-02]** Fixed: Both `_run_file_modifying_steps()` additions (gitignore negations + version write) consolidated into T014 sub-items (f) and (g).

---
*Generated by Copilot SDK (claude-opus-4.6)*
