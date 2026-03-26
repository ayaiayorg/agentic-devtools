# tasks.md

## Phase 1: Setup — Warning Audit Baseline

- [ ] T001 Run `agdt-test-pattern -W error --no-header -q` and capture full warning output to establish baseline before any changes
- [ ] T002 Categorise each captured warning as own-code DeprecationWarning, own-code UserWarning (intentional), or unavoidable third-party warning
- [ ] T003 Populate the Known Third-Party Warning Exemptions table in the spec with findings from T002; confirm `urllib3.exceptions.InsecureRequestWarning` is the only entry

## Phase 2: Foundational — Locate All Warning Emission and Capture Sites

- [ ] T004 [P] Grep entire test suite for `warnings.catch_warnings` usages; record file paths, line numbers, and whether each use is an assertion or a suppression
- [ ] T005 [P] Grep `agentic_devtools/` source for all `warnings.warn(` call sites; record file, line, category, message, and trigger condition to complete the Warning Emission Site inventory
- [ ] T006 Confirm that `sys` is imported at module scope in `agentic_devtools/cli/setup/gh_cli_installer.py` and note the exact line number of the `tar.extract(member, path=tmp_dir)` call (~line 198)

## Phase 3: US1 — Fix tarfile DeprecationWarning at Source

- [ ] T007 [US1] Write a failing test in `tests/unit/cli/setup/gh_cli_installer/` that patches `sys.version_info` to `(3, 12, 0)` and asserts `tar.extract()` is called with `filter="data"`
- [ ] T008 [US1] Write a failing test in `tests/unit/cli/setup/gh_cli_installer/` that patches `sys.version_info` to `(3, 11, 0)` and asserts `tar.extract()` is called without the `filter` kwarg
- [ ] T009 [US1] Ensure `__init__.py` files exist for any new test directories created in T007/T008; run `python scripts/validate_test_structure.py` to confirm structure is valid
- [ ] T010 [US1] Confirm that no duplicate `import sys` is introduced in
  `agentic_devtools/cli/setup/gh_cli_installer.py`; reuse the existing
  module-scope `sys` import when implementing the version-guarded
  `tar.extract()` change
- [ ] T011 [US1] Replace the bare `tar.extract(member, path=tmp_dir)` call in
  `agentic_devtools/cli/setup/gh_cli_installer.py` with the version-guarded
  form: `if sys.version_info >= (3, 12): tar.extract(member, path=tmp_dir, filter="data")` /
  `else: tar.extract(member, path=tmp_dir)`
- [ ] T012 [US1] Run `agdt-test-pattern tests/unit/cli/setup/gh_cli_installer/ -v` and confirm all tests pass including both new version-branch tests (T007, T008)

## Phase 4: US2 — Fix Autopilot Warning Test Patterns

- [ ] T013 [US2] For each `warnings.catch_warnings` site in
  `tests/unit/cli/copilot/session/test_start_copilot_session.py` identified in
  T004, classify each as assertion (warns expected) or suppression (warns
  incidental) and document the conversion target
- [ ] T014 [US2] Convert every intentional-assertion use of
  `warnings.catch_warnings(record=True)` in
  `tests/unit/cli/copilot/session/test_start_copilot_session.py` to
  `pytest.warns(UserWarning, match="<pattern>")`, removing the
  `warnings.simplefilter("always")` call and the post-hoc
  `assert any(...)` assertion
- [ ] T015 [US2] Update every incidental-suppression use of
  `warnings.catch_warnings` in
  `tests/unit/cli/copilot/session/test_start_copilot_session.py`: pass
  `autopilot=False` when the test is not exercising autopilot behaviour, or
  add `patch.object(session_module, "_get_copilot_binary", return_value="/usr/local/bin/copilot")`
  when a standalone binary path is needed
- [ ] T016 [US2] Apply the same intentional-vs-suppression classification and conversion from T013–T015 to any other test files identified in T004 that use `warnings.catch_warnings`
- [ ] T017 [US2] Remove any now-unused `import warnings` statements from test files modified in T014–T016 (check each file; remove only if `warnings` is no longer referenced)
- [ ] T018 [US2] Run `agdt-test-pattern tests/unit/cli/copilot/session/ -v` and confirm all tests pass with zero escaped `UserWarning` emissions

## Phase 5: US3 — Configure Global filterwarnings

- [ ] T019 [US3] Add the `filterwarnings` list to `[tool.pytest.ini_options]`
  in `pyproject.toml` with `"error"` as the first entry and
  `"ignore::urllib3.exceptions.InsecureRequestWarning"` as the only exemption;
  add additional `"ignore"` entries only for warnings confirmed in T002/T003
- [ ] T020 [US3] Verify `pyproject.toml` TOML syntax is valid by running
  `python -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))"`
  (Python 3.11+) or
  `pip install tomli && python -c "import tomli; tomli.load(open('pyproject.toml','rb'))"`
  (Python 3.10)
- [ ] T021 [US3] Run `agdt-test-pattern tests/ --co -q` (collection only, no test execution) and confirm zero errors, confirming the `filterwarnings` configuration is syntactically accepted by pytest
- [ ] T022 [US3] Run `agdt-test-pattern tests/unit/cli/copilot/session/ -v`
  again with `filterwarnings = ["error"]` now active to confirm no UserWarning
  escapes the `pytest.warns()` contexts added in Phase 4
- [ ] T023 [US3] Run `agdt-test-pattern tests/unit/cli/setup/gh_cli_installer/ -v` again with `filterwarnings = ["error"]` now active to confirm the tarfile fix eliminates the DeprecationWarning

## Final Phase: Polish & Cross-Cutting Verification

- [ ] T024 Run `agdt-test` (full suite with coverage, background task) to execute all 2000+ tests under the new `filterwarnings = ["error"]` configuration
- [ ] T025 Run `agdt-task-wait` and inspect the task log for any residual
  `DeprecationWarning`, `UserWarning`, `ResourceWarning`, or
  `PytestUnraisableExceptionWarning` lines; if any appear, categorise and
  apply the appropriate Phase 3/4/5 fix pattern before proceeding
- [ ] T026 Confirm coverage remains at 100%; if coverage drops due to the `sys.version_info >= (3, 12)` branch split, add branch-parametrized tests or version-patching to cover both paths
- [ ] T027 Run `bash scripts/run-pr-checks.sh` and confirm all steps exit 0, including the pytest step (step 2), ruff lint (step 4), ruff format (step 5), and markdownlint (step 6)
- [ ] T028 Run `python scripts/validate_test_structure.py` to confirm the 1:1:1 structure of all new test files added in Phase 3 passes CI enforcement
- [ ] T029 Commit all changes using `agdt-git-save-work` with a conventional
  commit message of the form
  `fix([#958](https://github.com/ayaiayorg/agentic-devtools/issues/958)): resolve test suite warnings with filterwarnings=error`
  and a matching footer line
  `[#958](https://github.com/ayaiayorg/agentic-devtools/issues/958)`,
  including the tarfile fix, pytest.warns conversions, autopilot=False
  updates, and filterwarnings config in the body; run `agdt-task-wait` to
  confirm the push succeeds

---
*Generated by Copilot SDK (gpt-5)*
