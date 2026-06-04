# Implementation Plan: Remove --no-deps Installs and Make github-copilot-sdk a Direct Dependency

## Technical Context

- **Package**: `agentic-devtools` — pip-installable Python CLI package
- **Build system**: Hatchling with hatch-vcs for versioning
- **Package metadata**: `pyproject.toml` at repo root
- **CI workflows**: GitHub Actions YAML under `.github/workflows/`
- **Testing**: pytest with 2000+ tests, run via `agdt-test` commands
- **Python**: >=3.10

### Key Files

| File | Role |
| --- | --- |
| `pyproject.toml` | Dependency declarations |
| `.github/workflows/ai-pr-loop.yml` | CI workflow with SDK install workaround |
| `.github/workflows/speckit-phase-progression.yml` | CI workflow with SDK install workaround |
| `.github/scripts/speckit-trigger/copilot_generate.py` | Script with diagnostic block |
| `tests/workflows/test_copilot_generate.py` | Tests asserting on diagnostic output |
| `CHANGELOG.md` | Release notes |

## Research Summary

See [research.md](research.md) for details on the dependency promotion strategy and backward compatibility.

## Design Overview

This is a **dependency hygiene** change, not a feature addition. The design is:

1. Promote `github-copilot-sdk` from optional to direct dependency in `pyproject.toml`
2. Remove the now-unnecessary `copilot-sdk` optional group
3. Simplify CI workflows to single `pip install` commands
4. Remove defensive diagnostic code from `copilot_generate.py`
5. Update tests that assert on removed diagnostic behavior
6. Document the change in CHANGELOG.md

## Implementation Phases

### Phase 1: Update `pyproject.toml` (FR-001, FR-002, FR-007)

**Deliverable**: SDK declared as direct dependency, optional group removed.

**Changes to `pyproject.toml`**:

1. Add `"github-copilot-sdk>=0.1.0,<1.0.0"` to `[project.dependencies]` list
2. Remove the entire `copilot-sdk = [...]` block from `[project.optional-dependencies]`
3. Leave `langchain` and `dev` optional groups untouched

**Verification**: `pip install -e .` in a clean venv installs the SDK automatically.

---

### Phase 2: Simplify CI Workflows (FR-003, FR-004)

**Deliverable**: Both workflows use single-command installs with no SDK workarounds.

#### `.github/workflows/ai-pr-loop.yml` (lines 62–66)

Replace:

```yaml
python -m pip install --upgrade pip
python -m pip install "github-copilot-sdk>=0.1.0,<1.0.0"
python -m pip install --force-reinstall --no-deps "github-copilot-sdk>=0.1.0,<1.0.0"
python -c "from copilot import CopilotClient, SubprocessConfig; from copilot.session import PermissionHandler; print('✓ Copilot SDK imports OK')"
python -m pip install agentic-devtools
```

With:

```yaml
python -m pip install --upgrade pip
python -m pip install agentic-devtools
python -c "from copilot import CopilotClient, SubprocessConfig; from copilot.session import PermissionHandler; print('✓ Copilot SDK imports OK')"
```

#### `.github/workflows/speckit-phase-progression.yml` (lines 483–487)

Replace:

```yaml
python -m pip install --upgrade pip
python -m pip install "github-copilot-sdk>=0.1.0,<1.0.0"
python -m pip install --force-reinstall --no-deps "github-copilot-sdk>=0.1.0,<1.0.0"
python -c "from copilot import CopilotClient, SubprocessConfig; from copilot.session import PermissionHandler; print('✓ Copilot SDK imports OK')"
python -m pip install . --no-deps
```

With:

```yaml
python -m pip install --upgrade pip
python -m pip install .
python -c "from copilot import CopilotClient, SubprocessConfig; from copilot.session import PermissionHandler; print('✓ Copilot SDK imports OK')"
```

---

### Phase 3: Remove Diagnostic Block from `copilot_generate.py` (FR-005)

**Deliverable**: Script uses standard Python import error propagation.

Replace lines 23–56 (the nested try/except with subprocess diagnostics):

```python
try:
    from copilot import CopilotClient, SubprocessConfig
    from copilot.session import PermissionHandler
except Exception as first_exc:
    try:
        from copilot import CopilotClient
        from copilot.config import SubprocessConfig
        from copilot.session import PermissionHandler
    except Exception as fallback_exc:
        error = first_exc if not isinstance(first_exc, ImportError) else fallback_exc
        pip_show = subprocess.run(...)
        ...
        sys.exit(1)
```

With simplified import handling:

```python
try:
    from copilot import CopilotClient, SubprocessConfig
    from copilot.session import PermissionHandler
except ImportError:
    from copilot import CopilotClient
    from copilot.config import SubprocessConfig
    from copilot.session import PermissionHandler
```

This preserves the fallback for different SDK versions (where `SubprocessConfig` moved between modules) but removes all subprocess diagnostic code. If both import paths fail, the `ImportError`
propagates naturally with a standard Python traceback.

Also remove `import subprocess` from the top of the file if no longer used elsewhere.

---

### Phase 4: Update Tests (FR-006)

**Deliverable**: All tests pass; diagnostic-related assertions removed.

**File**: `tests/workflows/test_copilot_generate.py`

- **Remove** `TestImportFailurePath.test_import_failure_exits_with_status_1_and_prints_diagnostics` — this test validates removed diagnostic behavior
- **Remove** `TestImportFailurePath.test_import_failure_warns_about_conflicting_copilot_package` — this test validates removed conflicting-package detection
- **Add** a new test verifying that when SDK import fails, an `ImportError` propagates naturally (no `sys.exit(1)`, no subprocess calls)

---

### Phase 5: CHANGELOG Entry (FR-008)

**Deliverable**: CHANGELOG.md updated under `[Unreleased]`.

Add under `### Changed`:

```markdown
### Changed

- `github-copilot-sdk` is now a direct dependency installed automatically with `agentic-devtools`.
  The `copilot-sdk` optional extra has been removed. Users previously installing with
  `pip install agentic-devtools[copilot-sdk]` should switch to `pip install agentic-devtools`.
```

---

### Phase 6: Validation

1. Run `agdt-test` / `agdt-task-wait` — full test suite must pass
2. Run `bash scripts/targeted-checks.sh` — lint, format, type-check
3. Verify `pip install -e .` in clean venv installs SDK
4. Verify `python -c "from copilot import CopilotClient"` succeeds post-install

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| SDK not available on PyPI during CI run | Low | High (install fails entirely) | This is correct behavior per spec; pip cache reduces likelihood |
| Other workflows reference SDK install pattern | Low | Medium | Grep confirmed only 2 workflows affected |
| Tests rely on diagnostic output beyond identified ones | Low | Low | Full test suite run in Phase 6 catches any missed assertions |
| SDK transitive deps conflict with existing deps | Low | Medium | Verify with `pip check` after install |
| Users with `agentic-devtools[copilot-sdk]` get warning | Certain | Low | Pip only warns (doesn't fail) on unknown extras; CHANGELOG documents migration |

## Dependencies

- **External**: `github-copilot-sdk` package on PyPI (already consumed today)
- **Internal**: No other agentic-devtools modules need changes — the SDK is only imported in `copilot_generate.py`
- **Blocking**: None — this change is self-contained

---
*Generated by Copilot SDK (claude-opus-4.6)*
