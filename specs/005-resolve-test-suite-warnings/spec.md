# Spec 005 — Resolve Test Suite Warnings

## 1. Overview

The current Python test suite for `agentic-devtools` emits warnings during normal runs (both locally and in CI). These warnings come from a mix of:

- Our own code (e.g., deprecation paths, feature flags)
- Python standard library behavior changes across versions
- Third-party libraries (e.g., `pytest`, HTTP clients, `tarfile`)

This specification defines how we will:

- Reduce warning noise to zero for our own code and for controllable third-party behavior
- Treat **unexpected warnings as test failures** in CI
- Provide explicit, documented exemptions for any remaining unavoidable warnings
- Keep the solution robust across supported Python versions and platforms

The outcome should be a **clean, deterministic, warning-free test run by default**, with intentional warnings tested explicitly and protected against regressions.

## 2. Goals and Non-Goals

### 2.1 Goals

- **G1 — Clean default test run**: `agdt-test` and `agdt-test-quick` must complete without emitting any warnings, on all supported Python versions and supported platforms, given a correctly configured environment.
- **G2 — CI enforcement**: Any **unexpected** warning (originating from tests or production code under test) must cause CI test jobs to fail (non-zero exit).
- **G3 — Intentional warning coverage**: Where our code legitimately emits warnings (e.g., deprecated CLI flags, behavioral guards), these must be:
  - Covered by explicit tests that assert the warning via `pytest.warns` or equivalent, and
  - Not leak warnings into the overall test output.
- **G4 — Documented exemptions**: Any unavoidable third-party warning must be listed in a known exemptions table, with a documented rationale, and a corresponding `filterwarnings` ignore entry.

### 2.2 Non-Goals

- **Not fixing third-party library internals**: We will not fork or modify third-party packages to eliminate their warnings.
- **Not changing production warning behavior**: The `warnings.warn()` calls in production code are intentional and will not be removed — only the test patterns around them change.
- **Not upgrading library versions**: If a third-party library emits warnings, we will add exemptions rather than upgrading the library in this spec's scope.

## 3. Clarifications (Resolved Ambiguities)

1. **`filter` value for tar**: Use `"data"` (Python security advisory recommendation; strips path traversal and special files).
2. **Python 3.10/3.11 compatibility**: Use `sys.version_info >= (3, 12)` version guard; the `filter` kwarg is omitted on older Pythons where the `DeprecationWarning` isn't emitted.
3. **Autopilot warning fix strategy**: Intentional warning tests use `pytest.warns(UserWarning, match="--autopilot is not supported")`; all other tests pass `autopilot=False` or mock `_get_copilot_binary`.
4. **`filterwarnings` scope**: Global `"error"` with explicit `ignore` entries only for unavoidable third-party warnings.
5. **CI enforcement**: Hard failure (non-zero pytest exit), not informational.

## 4. User Stories

### US1 — Fix tarfile DeprecationWarning at Source

**As a** developer running the test suite on Python 3.12+,
**I want** the `tarfile.extract()` call in `gh_cli_installer.py` to use the `filter="data"` kwarg,
**so that** no `DeprecationWarning` is emitted during test execution.

**Acceptance Criteria:**

- AC1.1: On Python 3.12+, `tar.extract()` is called with `filter="data"`.
- AC1.2: On Python 3.10/3.11, `tar.extract()` is called without the `filter` kwarg (kwarg not available).
- AC1.3: Both version branches are covered by unit tests that verify the correct call signature.
- AC1.4: No `DeprecationWarning` from `tarfile` appears in test output on any supported Python version.

### US2 — Fix Autopilot Warning Test Patterns

**As a** developer maintaining the copilot session tests,
**I want** all tests that assert on intentional `UserWarning` emissions to use `pytest.warns()` instead of raw `warnings.catch_warnings(record=True)`,
**so that** warnings are properly captured and do not leak into the global test output.

**Acceptance Criteria:**

- AC2.1: All intentional-assertion tests in `test_start_copilot_session.py` and `test__build_copilot_args.py` use `pytest.warns(UserWarning, match="<pattern>")`.
- AC2.2: All incidental-suppression tests either pass `autopilot=False` or mock `_get_copilot_binary` to prevent the warning from being emitted.
- AC2.3: No `UserWarning` from the autopilot fallback appears in non-intentional test output.
- AC2.4: All `import warnings` statements that are no longer needed are removed from modified test files.

### US3 — Configure Global filterwarnings

**As a** CI pipeline maintainer,
**I want** `pyproject.toml` to configure `filterwarnings = ["error"]` globally,
**so that** any unhandled warning causes the test run to fail with a non-zero exit code.

**Acceptance Criteria:**

- AC3.1: `[tool.pytest.ini_options]` in `pyproject.toml` includes `filterwarnings = ["error", ...]`.
- AC3.2: Unavoidable third-party warnings (e.g., `urllib3.exceptions.InsecureRequestWarning`) have explicit `ignore` entries.
- AC3.3: The full test suite passes with zero warnings under the new configuration.
- AC3.4: `pytest --co -q` (collection only) succeeds without errors, confirming syntactic validity.

## 5. Functional Requirements

| ID | Priority | Requirement |
|----|----------|-------------|
| FR1 | **Must** | Add `filter="data"` kwarg to `tar.extract()` in `gh_cli_installer.py`, guarded by `sys.version_info >= (3, 12)` |
| FR2 | **Must** | Convert all intentional-warning tests from `warnings.catch_warnings(record=True)` to `pytest.warns(UserWarning, match="<pattern>")` |
| FR3 | **Must** | Prevent incidental autopilot warnings in non-intentional tests by passing `autopilot=False` or mocking `_get_copilot_binary` |
| FR4 | **Must** | Add `filterwarnings = ["error"]` to `[tool.pytest.ini_options]` in `pyproject.toml` |
| FR5 | **Must** | Add `"ignore::urllib3.exceptions.InsecureRequestWarning"` exemption in `filterwarnings` list |
| FR6 | **Should** | Remove unused `import warnings` statements from test files after conversion |

## 6. Key Entities

| Entity | Location | Role |
|--------|----------|------|
| `tar.extract()` call | `agentic_devtools/cli/setup/gh_cli_installer.py:198` | Source of `DeprecationWarning` on Python 3.12+ |
| `warnings.warn("--autopilot is not supported…")` | `agentic_devtools/cli/copilot/session.py:287-290` | Intentional `UserWarning` for autopilot fallback |
| `warnings.warn("gh copilot is not available…")` | `agentic_devtools/cli/copilot/session.py:504-507` | Intentional `UserWarning` for copilot unavailability |
| `warnings.warn("Prompt truncated…")` | `agentic_devtools/cli/copilot/session.py:402-419` | Intentional `UserWarning` for prompt truncation |
| `warnings.filterwarnings("ignore", category=InsecureRequestWarning)` | `agentic_devtools/cli/jira/helpers.py:35-39` | Source-level suppression of urllib3 warning |
| `filterwarnings` config | `pyproject.toml [tool.pytest.ini_options]` | Global warning-to-error promotion |

## 7. Non-Functional Requirements

| ID | Requirement | Measurement |
|----|-------------|-------------|
| NFR1 | `pytest` exits with code 0 when `filterwarnings = ["error"]` is active | Full test suite exit code |
| NFR2 | No `DeprecationWarning` from `tarfile` on Python 3.12+ | Grep test output for `DeprecationWarning` |
| NFR3 | No escaped `UserWarning` from autopilot in non-intentional tests | Grep test output for `UserWarning` |
| NFR4 | All intentional-warning tests use `pytest.warns()` assertions | Code review / grep for `catch_warnings` |
| NFR5 | Test coverage remains at 100% | `--cov-fail-under=100` |
| NFR6 | `scripts/run-pr-checks.sh` exits 0 | CI pipeline status |

## 8. Edge Cases

| ID | Scenario | Expected Behavior |
|----|----------|-------------------|
| EC1 | `filter="data"` rejects a valid binary tar member | Should not occur: the `gh` binary is a plain regular file with a relative path. `filter="data"` only rejects dangerous entries (absolute paths, device files, symlinks to outside). |
| EC2 | `ResourceWarning` from unclosed file handles in other tests | Surfaced by `filterwarnings = ["error"]` during Phase 1 audit. Fix by using context managers correctly in affected tests. |
| EC3 | A test imports `session.py` indirectly, triggering autopilot warning | Phase 1 audit identifies all emission sites. Apply `autopilot=False` or mock `_get_copilot_binary` pattern. |
| EC4 | New third-party library version starts emitting warnings | Add to Known Third-Party Warning Exemptions table, then add `ignore` entry to `filterwarnings`. |
| EC5 | `pytest.warns()` raises if no warning is emitted | Ensure the code path under test actually calls `warnings.warn()`. The conversion is 1:1 from existing `catch_warnings` assertions. |

## 9. Known Third-Party Warning Exemptions

| Warning Class | Source Package | Reason Unavoidable |
|---------------|----------------|-------------------|
| `urllib3.exceptions.InsecureRequestWarning` | urllib3 | Jira SSL-verify=False code path; suppressed in source but may fire before module init |

> This table will be populated with additional entries during the Phase 1 audit if new unavoidable warnings are discovered.

## 10. Success Criteria

| ID | Criterion |
|----|-----------|
| SC1 | `pytest` exits with code 0 with `filterwarnings = ["error"]` active |
| SC2 | No `DeprecationWarning` from `tarfile` on Python 3.12+ |
| SC3 | No `UserWarning` from autopilot fallback in non-intentional tests |
| SC4 | Intentional-warning tests use `pytest.warns()` assertions |
| SC5 | `run-pr-checks.sh` exits 0 |
| SC6 | Coverage remains at 100% |

## 11. Out of Scope

- Fixing warnings emitted by third-party libraries (only add exemptions)
- Upgrading third-party library versions to eliminate their warnings
- Modifying test logic for reasons unrelated to warning suppression
- Changing production warning behavior (the `warnings.warn()` calls are intentional)

## 12. Implementation Notes

### Safe Sequencing Order

1. **Audit** — Establish warning baseline
2. **Fix source** — `tarfile.extract()` version guard
3. **Fix tests** — Convert `warnings.catch_warnings` to `pytest.warns()`
4. **Add `filterwarnings = ["error"]`** — Global promotion
5. **Full verification** — Suite-wide validation

### Preference Rule for Suppression Strategy (FR3)

When preventing incidental autopilot warnings in tests:

- **Prefer** `autopilot=False` — when the test does not exercise autopilot behavior
- **Use mock** `_get_copilot_binary` — only when the test exercises binary-resolution logic independent of autopilot

---

**Source Issue**: [#958](https://github.com/ayaiayorg/agentic-devtools/issues/958)
