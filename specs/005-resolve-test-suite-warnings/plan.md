# Implementation Plan: Resolve Test Suite Warnings (Spec 005)

## 1. Technical Context

- **Language**: Python 3.10+ (target version from `pyproject.toml`; CI also runs 3.12+)
- **Test framework**: pytest with `--cov=agentic_devtools --cov-fail-under=100`
- **Warning system**: Python `warnings` module + pytest's `filterwarnings` ini option
- **Key source files**:
  - `agentic_devtools/cli/setup/gh_cli_installer.py` — uses `tarfile.extract()` without `filter=`
  - `agentic_devtools/cli/copilot/session.py` — emits `UserWarning` via `warnings.warn()` for autopilot fallback
  - `agentic_devtools/cli/jira/helpers.py` — suppresses `InsecureRequestWarning` inside the `_get_requests()` helper (lazy import, not at module import time)
- **Key test files**:
  - `tests/unit/cli/copilot/session/test_start_copilot_session.py` — catches autopilot `UserWarning` via raw `warnings.catch_warnings(record=True)`; this pattern is not pytest-native and leaks warnings
  - `tests/unit/cli/setup/gh_cli_installer/test_download_and_install.py` — creates in-memory tar archives as fixtures
    and calls `download_and_install(...)`, which in turn uses `tarfile.extract()`
    (so these tests do exercise the `extract` code path and can trigger its warnings)
- **CI scripts**: `scripts/run-pr-checks.sh` (step 2 runs pytest; failures propagate via `set -euo pipefail`)

## 2. Research Summary

Key research decisions (summarized here):

| Decision | Choice |
|---|---|
| `filterwarnings` scope | Global `"error"` in `pyproject.toml` + `ignore` entries only for unavoidable third-party warnings |
| `tarfile.extract` fix | Add `filter="data"` kwarg guarded by `sys.version_info >= (3, 12)` |
| Autopilot warning tests | Convert to `pytest.warns(UserWarning, match="...")` for intentional tests; pass `autopilot=False` or mock `_get_copilot_binary` everywhere else |
| CI enforcement | Existing `set -euo pipefail` in `run-pr-checks.sh` already propagates pytest failures — no script change needed |
| urllib3 `InsecureRequestWarning` | Already suppressed in `_get_requests()` helper (`jira/helpers.py`); add `filterwarnings` exemption as belt-and-suspenders |

## 3. Design Overview

The core mechanism is:

```text
pyproject.toml filterwarnings = ["error"]
        │
        ├─► Any unhandled warning → test FAILS (hard, non-zero exit)
        │
        ├─► tarfile DeprecationWarning → eliminated at source (filter="data")
        │
        ├─► autopilot UserWarning → asserted with pytest.warns() (intentional)
        │   └─► all other copilot tests → autopilot=False or mock binary
        │
        └─► third-party InsecureRequestWarning → ignore exemption entry
```

No new test infrastructure is needed. All changes are surgical: one `pyproject.toml` stanza, one source fix, and test adjustments in the copilot session tests.

## 4. Implementation Phases

### Phase 1 — Audit (prerequisite, read-only)

**Goal**: Establish a complete baseline of all warnings currently emitted.

**Steps**:

1. Run `agdt-test-pattern tests/ -W error --no-header -q 2>&1` to surface all promotion candidates
   without `filterwarnings` in `pyproject.toml` yet, then scan the output (optionally using a
   platform-appropriate filtering tool such as `grep` on POSIX shells or `Select-String` in
   PowerShell) for lines containing `Warning`, `FAILED`, or `ERROR`.
2. Categorise each warning:
   - **Own code DeprecationWarning** → fix at source
   - **Own code UserWarning (intentional)** → assert with `pytest.warns()`
   - **Third-party unavoidable** → add `ignore` exemption
3. Populate the "Known Third-Party Warning Exemptions" table in this plan's appendix.

**Deliverable**: Categorised warning inventory.

---

### Phase 2 — Fix `tarfile.extract()` (source fix)

**Goal**: Eliminate the Python 3.12+ `DeprecationWarning` from `gh_cli_installer.py`.

**File**: `agentic_devtools/cli/setup/gh_cli_installer.py`

**Change**: Wrap the `tar.extract()` call with a version guard:

```python
import sys

# inside the extraction block, replacing the bare tar.extract(member, path=tmp_dir):
if sys.version_info >= (3, 12):
    tar.extract(member, path=tmp_dir, filter="data")
else:
    tar.extract(member, path=tmp_dir)
```

**Why `filter="data"`**: Strips path-traversal sequences and special files (devices, symlinks to absolute paths). Python security advisory
recommendation. Safe for this use-case — we're extracting a single, name-validated `gh` binary from a trusted GitHub release archive.

**Verification**: `agdt-test-pattern tests/unit/cli/setup/gh_cli_installer/ -v` — all tests still pass; no `DeprecationWarning` emitted.

---

### Phase 3 — Fix autopilot warning tests

**Goal**: Replace all raw `warnings.catch_warnings(record=True)` with pytest-native patterns so the global `"error"` filter doesn't break them.

**File**: `tests/unit/cli/copilot/session/test_start_copilot_session.py`

#### 3a — Intentional-warning tests

Tests that *assert* that a warning is emitted must be converted to `pytest.warns()`:

```python
# BEFORE
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    start_copilot_session(prompt="...", working_directory=str(temp_state))
assert any("--autopilot is not supported" in str(warning.message) for warning in w)

# AFTER
with pytest.warns(UserWarning, match="--autopilot is not supported"):
    start_copilot_session(prompt="...", working_directory=str(temp_state))
```

Apply the same conversion to any other test that currently uses `warnings.catch_warnings(record=True)` as an assertion mechanism.

#### 3b — Tests that suppress warnings to silence them (not assert)

Any test that wraps `start_copilot_session(...)` in `with warnings.catch_warnings(record=True):` purely to silence an incidental autopilot warning must instead prevent the warning from being emitted:

```python
# Option A: pass autopilot=False when it isn't the thing under test
start_copilot_session(prompt="...", working_directory=str(temp_state), autopilot=False)

# Option B: mock _get_copilot_binary so the standalone branch is taken (no warning)
with patch.object(session_module, "_get_copilot_binary", return_value="/usr/local/bin/copilot"):
    start_copilot_session(...)
```

**Audit target**: Search for every `warnings.catch_warnings` call in the test suite and apply the correct pattern from 3a or 3b.

**Verification**: `agdt-test-pattern tests/unit/cli/copilot/session/ -v` — all pass with zero stray warnings.

---

### Phase 4 — Configure global `filterwarnings`

**Goal**: Promote all unhandled warnings to errors in the pytest run.

**File**: `pyproject.toml`, `[tool.pytest.ini_options]`

**Change**: Add after the `markers` list:

```toml
filterwarnings = [
    "error",
    # urllib3 InsecureRequestWarning is suppressed at source in jira/helpers.py;
    # this entry is a belt-and-suspenders guard for any test that imports the
    # module before the suppression fires.
    "ignore::urllib3.exceptions.InsecureRequestWarning",
]
```

> **Note**: Populate additional `ignore` entries only from the Phase 1 audit. The table below is a living record — add entries as new unavoidable third-party warnings are confirmed.

**Known third-party exemptions discovered during audit**:

| Warning class | Source package | Reason unavoidable |
|---|---|---|
| `urllib3.exceptions.InsecureRequestWarning` | urllib3 | Jira SSL-verify=False code path; suppressed in source but may fire before module init |

**Verification**: Run `agdt-test-pattern tests/ --co -q` (collection only) — zero errors means the configuration is syntactically valid. Then run the full suite.

---

### Phase 5 — Full suite verification

**Goal**: Confirm zero warnings, zero failures, 100% coverage.

**Steps**:

1. `agdt-test` (full suite with coverage, background task)
2. `agdt-task-wait`
3. Inspect log — look for any `PytestUnraisableExceptionWarning`, `DeprecationWarning`, `ResourceWarning`, or `UserWarning` lines.
4. If any new warning surfaces: categorise and apply Phase 2/3/4 fix.
5. `bash scripts/run-pr-checks.sh` — all 8 steps must pass.

**Success criteria** (from spec):

- [ ] `pytest` exits with code 0 with `filterwarnings = ["error"]` active
- [ ] No `DeprecationWarning` from `tarfile` on Python 3.12+
- [ ] No `UserWarning` from autopilot fallback in non-intentional tests
- [ ] Intentional-warning tests use `pytest.warns()` assertions
- [ ] `run-pr-checks.sh` exits 0
- [ ] Coverage remains at 100%

---

## 5. Risk Assessment

| Risk | Likelihood | Mitigation |
|---|---|---|
| Additional third-party warnings discovered in Phase 1 audit | Medium | Audit first; only add `ignore` entries for confirmed unavoidable warnings |
| `filter="data"` changes extraction behaviour (e.g., rejects the gh binary member) | Low | The member is a plain regular file with a relative path — `filter="data"` only strips dangerous entries; test suite covers the extraction path |
| `pytest.warns()` raises if no warning is emitted | Low | Already confirmed that `session.py` emits `UserWarning` via `warnings.warn()` when the fallback branch is taken; the conversion is 1:1 |
| Other test files that import `session.py` indirectly trigger autopilot warning | Medium | Phase 1 audit identifies all emission sites; Phase 3 applies fixes broadly |
| `ResourceWarning` from unclosed file handles in other tests | Low | Will appear in Phase 1 audit; fix by using context managers correctly |
| Coverage drops below 100% if new code path added for version guard | Low | Both branches of the `sys.version_info` guard are testable by patching; the existing gh_cli_installer tests already exercise the extraction path |

## 6. Dependencies

### External

- Python 3.12+ to reproduce the `tarfile` `DeprecationWarning` locally (CI covers this)
- No new third-party packages required

### Internal

- Phase 1 (audit) must complete before Phase 4 (configure `filterwarnings`) — the `ignore` list depends on what the audit finds
- Phase 2 and Phase 3 are independent — can be done in parallel
- Phase 4 depends on Phases 2 and 3 being complete (otherwise promoting warnings to errors will fail the suite immediately)
- Phase 5 depends on all prior phases

### Safe sequencing order (from spec Implementation Notes)

1. Audit → 2. Fix source → 3. Fix tests → 4. Add `filterwarnings = ["error"]` → 5. Full verification

---
*Generated by Copilot SDK (gpt-5)*
