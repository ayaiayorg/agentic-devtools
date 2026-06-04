# Implementation Plan: Upgrade to github-copilot-sdk v1

## Technical Context

- **Language/Runtime**: Python 3.x
- **Package Manager**: pip with `pyproject.toml`
- **Dependency**: `github-copilot-sdk` (optional, under `[project.optional-dependencies].copilot-sdk`)
- **Key File**: `agentic_devtools/cli/ci/github_provider.py` (~2700+ lines, 4 identical import shim blocks)
- **CI Workflows**: `.github/workflows/ai-pr-loop.yml`, `.github/workflows/speckit-phase-progression.yml`
- **External Script**: `.github/scripts/speckit-trigger/copilot_generate.py`
- **Test Framework**: pytest with `unittest.mock`

## Research Summary

See [research.md](research.md) for details on:

- Import path changes between v0 and v1
- Retained graceful degradation pattern
- Mock strategy for tests

## Design Overview

This is a **mechanical refactoring** — no architectural changes. The work consists of:

1. Updating the version constraint in `pyproject.toml`
2. Replacing 4 identical try/except shim blocks in production code with direct v1 imports
3. Updating 1 external script's import block
4. Updating 2 CI workflow files (install commands + smoke-check lines)
5. Updating 4 test files to remove fallback-path test cases and update mock targets

The **outer `except Exception` → return None/raise** pattern for SDK-unavailable environments is **retained**
at all call sites.

## Implementation Phases

### Phase 1: Dependency Constraint Update

**Deliverable**: `pyproject.toml` updated

| File | Change |
| --- | --- |
| `pyproject.toml` line 31 | `"github-copilot-sdk>=0.1.0,<1.0.0"` → `"github-copilot-sdk>=1.0.0,<2.0.0"` |

### Phase 2: Production Code — Import Path Migration

**Deliverable**: All 4 shim blocks in `github_provider.py` + 1 in `copilot_generate.py` updated

**Pattern (before):**

```python
try:
    from copilot import CopilotClient, SubprocessConfig
    from copilot.session import PermissionHandler
except Exception as primary_exc:
    try:
        from copilot import CopilotClient
        from copilot.config import SubprocessConfig
        from copilot.session import PermissionHandler
    except Exception as exc:
        # graceful degradation
```

**Pattern (after):**

```python
try:
    from copilot import CopilotClient
    from copilot.config import SubprocessConfig
    from copilot.session import PermissionHandler
except Exception as exc:
    # graceful degradation (unchanged)
```

**Locations in `github_provider.py`:**

1. Lines 1496–1509 (squash commit message generation)
2. Lines 1612–1625 (conflict resolution)
3. Lines 2550–2562 (comment verification)
4. Lines 2677–2687 (run prompt via SDK)

**Location in `copilot_generate.py`:**

1. Lines 23–55 (top-level import block — remove entire shim, keep only v1 imports with graceful degradation)

### Phase 3: CI Workflow Updates

**Deliverable**: 2 workflow files updated

| File | Line | Change |
| --- | --- | --- |
| `.github/workflows/ai-pr-loop.yml` | 63–65 | Update version constraint to `>=1.0.0,<2.0.0` and smoke-check to v1 paths |
| `.github/workflows/speckit-phase-progression.yml` | 484–486 | Same changes |

**Smoke-check (before):**

```bash
python -c "from copilot import CopilotClient, SubprocessConfig; from copilot.session import PermissionHandler; print('✓ Copilot SDK imports OK')"
```

**Smoke-check (after):**

```bash
python -c "from copilot import CopilotClient; from copilot.config import SubprocessConfig; from copilot.session import PermissionHandler; print('✓ Copilot SDK imports OK')"
```

### Phase 4: Test Updates

**Deliverable**: All test files updated to mock v1 paths and remove fallback tests

| Test File | Changes Required |
| --- | --- |
| `tests/unit/cli/ci/github_provider/test_finalize_post_repair.py` | Remove `_build_sdk_modules_no_subprocess_config` helper and `test_run_prompt_via_sdk_fallback_import_path_succeeds` test. Update remaining mocks to target `copilot.config.SubprocessConfig`. |
| `tests/unit/cli/ci/github_provider/test__generate_commit_message_via_sdk.py` | Remove `_build_sdk_mocks_no_subprocess_config` helper and fallback test. Update `mock_copilot.SubprocessConfig` → mock `copilot.config` module. |
| `tests/unit/cli/ci/github_provider/test__resolve_conflicted_file_content_via_sdk.py` | Same pattern as above — remove fallback helper/test, update mocks. |
| `tests/workflows/test_copilot_generate.py` | Update mock targets from `copilot.SubprocessConfig` to `copilot.config.SubprocessConfig`. Remove any fallback-path assertions. |

**Mock pattern (after):**

Tests should patch `sys.modules` with:

```python
{
    "copilot": mock_copilot,          # has CopilotClient
    "copilot.config": mock_config,    # has SubprocessConfig
    "copilot.session": mock_session,  # has PermissionHandler
}
```

### Phase 5: Validation

**Deliverable**: All checks pass

1. Run `agdt-test` (full suite with coverage)
2. Run `bash scripts/targeted-checks.sh` (ruff, mypy, markdownlint)
3. Verify no remaining references to old import pattern: `grep -r "from copilot import.*SubprocessConfig"`
4. Verify no remaining shim blocks: `grep -rn "except.*primary_exc\|except.*first_exc" agentic_devtools/ .github/`

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| v1 SDK has undocumented API changes beyond imports | Low | Medium | Existing fallback code already uses v1 paths successfully; clarifications confirm API unchanged |
| Tests that mock SDK internals become flaky | Low | Low | Mock at module level (`sys.modules`) — same pattern, just different key names |
| CI environment cannot install `>=1.0.0` | Low | High | Verify PyPI availability before merging; the SDK v1 already exists per research |
| `copilot_generate.py` diagnostic removal breaks error reporting | Low | Low | Issue #1756 (separate spec) covers full diagnostic removal; this PR only updates the import path, retaining the diagnostic block structure |

## Dependencies

- **External**: `github-copilot-sdk>=1.0.0` must be available on PyPI
- **Internal**: No dependency on other in-flight PRs
- **Related**: Issue #1756 (make SDK a direct dependency) should be sequenced *after* this upgrade lands
- **Branch**: Work on `speckit/1755/phase-2-clarify` or create implementation branch from it

---
*Generated by Copilot SDK (claude-opus-4.6)*
