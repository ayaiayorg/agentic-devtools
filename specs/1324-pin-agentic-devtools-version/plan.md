# Implementation Plan: Pin agentic-devtools Version & Guard agdt-setup

**Issue**: [#1324](https://github.com/ayaiayorg/agentic-devtools/issues/1324)

## Technical Context

- **Language**: Python 3.10+, pip-installable package
- **Build system**: Hatchling + hatch-vcs (version from git tags → `_version.py`)
- **Setup entry point**: `agentic_devtools/cli/setup/commands.py` → `setup_cmd()`
- **Config persistence**: `agentic_devtools/cli/config/project_config.py` (load/save `.agdt/config/project.json`)
- **Gitignore management**: `agentic_devtools/agdt_gitignore.py` (manages `.agdt/.gitignore`)
- **Version source**: `agentic_devtools.__version__` (re-exported from `_version.py`)
- **Test framework**: pytest, 1:1:1 test structure under `tests/unit/`
- **Existing dependencies**: `packaging` is NOT in explicit deps (needs adding)

## Research Summary

Key design decisions (from research phase):

- Version comparison strategy: `packaging.version.Version` with segment-based fallback
- Placement of version guard in `setup_cmd()` flow: after argparse + git_root, before local-only steps
- Gitignore negation rule ordering: `!.agdt/config/` before `!.agdt/config/project.json`

## Design Overview

```text
┌─────────────────────────────────────────────────────────────────┐
│ setup_cmd()                                                      │
├─────────────────────────────────────────────────────────────────┤
│ 1. argparse (+ new --force-old-version flag)                     │
│ 2. git_root = _get_git_repo_root()                               │
│ 3. ★ VERSION GUARD ← new logic                                  │
│    ↳ older + no force → sys.exit(1) (fail-fast, nothing else)    │
│    ↳ older + force → set skip_repo_steps flag                    │
│ 4. SSL, banner, managed installs (local-only)                    │
│ 5. dependency check, env persist (local-only)                    │
│ 6. _run_file_modifying_steps() (skipped when force flag set)     │
│    ├─ ensure_agdt_gitignore()                                    │
│    ├─ ★ ensure_root_gitignore_negations() ← new                 │
│    ├─ project config prompts                                     │
│    ├─ skill injection                                            │
│    ├─ platform detection + adapter                               │
│    ├─ template generation                                        │
│    └─ ★ write agdt_version to project.json ← new (LAST step)    │
│ 7. PR workflow wrapping (branch, commit, push, PR)               │
└─────────────────────────────────────────────────────────────────┘
```

**Key design note**: The version guard must execute AFTER `git_root` detection but BEFORE `_run_file_modifying_steps()`. When `--force-old-version` is active, local-only steps (cert prefetch, managed
installs, dependency checks, shell profile persistence) still execute, but `_run_file_modifying_steps()` is skipped entirely.

**Re-reading the spec more carefully**: The spec says in the non-force mismatch path (Story 2), the command fails fast with non-zero exit — **no local-only steps execute**. This means the version
guard needs to execute BEFORE local-only steps as well. But wait — the spec also says: "The version guard MUST execute immediately after argparse parsing and git root detection, but BEFORE any
file-modifying steps." And the clarification says "Cert prefetch and managed installs are local-only steps that execute **after** the version guard in the flow."

So the actual flow is:

1. argparse
2. git_root detection
3. **VERSION GUARD** ← fails fast here if older + no force (exit non-zero, nothing else runs)
4. If force → set flag to skip file-modifying steps; continue to local-only steps
5. Local-only steps (cert prefetch, installs, dependency check, env persist)
6. If not force-skipped → `_run_file_modifying_steps()`

This requires restructuring `setup_cmd()` to move `git_root` detection earlier
(currently after the local-only steps such as cert prefetch and managed installs).
The restructure is minimal — just move the `_get_git_repo_root()` call up to immediately after argparse.

## Implementation Phases

### Phase 1: Version Comparison Module (New File)

**Deliverable**: `agentic_devtools/cli/setup/version_guard.py`

**Tasks**:

1. Create `version_guard.py` with:
   - `compare_versions(running: str, pinned: str) -> int` — returns -1 (older), 0 (equal), 1 (newer)
   - Uses `packaging.version.Version` with fallback to segment-based comparison per NFR-003
   - `check_version_guard(git_root: Path | None, force_old_version: bool) -> str | None`
     - Returns `None` if guard passes (proceed normally)
     - Returns `"block"` if older + no force (caller should exit)
     - Returns `"force"` if older + force flag (caller should skip repo steps)
   - `_fallback_compare(running: str, pinned: str) -> int` — segment-based fallback
   - **FR-011 (malformed version handling)**: When `agdt_version` in `project.json` is
     present but unparseable (not a valid version string), log a warning to stderr and
     proceed normally (return `None`) — never block setup due to a corrupt pin value
   - **FR-005/FR-009 (mismatch messaging)**: When a version mismatch is detected, emit a structured diagnostic to **stderr** containing:
     - The currently running version
     - The required (pinned) version from `project.json`
     - The upgrade command (`python setup-dev-tools.py`)
     - The `--force-old-version` flag as an override escape hatch
   - **FR-009 (force-old-version warning)**: When `--force-old-version` is active and the
     running version is older than the pinned version, emit a **warning** to **stderr**
     stating that repo files will not be modified and that this mode is not recommended.
     This warning is distinct from the error diagnostic above — it fires only in the
     force path (guard returns `"force"`), not in the block path.
2. Add `"packaging>=21.0"` to `[project.dependencies]` in `pyproject.toml` and run `pip install -e .` to verify

**Tests** (`tests/unit/cli/setup/version_guard/`):

- `test_compare_versions.py` — PEP 440 cases (normal, pre-release, dev, post)
- `test__fallback_compare.py` — segment-based logic with edge cases
- `test_check_version_guard.py` — integration of guard logic with project.json, including:
  - FR-011: malformed `agdt_version` values (empty string, non-semver garbage, None) → returns `None` with warning logged
  - FR-005/FR-009: mismatch scenario prints running version, required version, upgrade command, and `--force-old-version` hint to stderr
  - US3/AS4: `check_version_guard(..., force_old_version=True)` returns `None` (and does not emit a warning) when
    `running >= pinned`, confirming the flag is a safe no-op when the version constraint is already satisfied
  - FR-009 (force warning): when `--force-old-version` is active and running < pinned,
    assert a warning is emitted to stderr stating repo files will not be modified and
    the mode is not recommended

### Phase 2: Root Gitignore Negation Helper (New File)

**Deliverable**: `agentic_devtools/cli/setup/gitignore_negations.py`

**Tasks**:

1. Create `ensure_root_gitignore_negations(git_root: Path) -> bool`
   - Reads root `.gitignore`
   - Finds the `.agdt/` ignore line
   - Inserts `!.agdt/`, `!.agdt/config/`, `!.agdt/config/project.json` after it (if not already present)
   - Idempotent — skips if negation rules already exist
   - Returns `True` if file was modified, `False` otherwise
2. Handle edge cases: no `.gitignore` exists, no `.agdt/` rule found, file not writable

**Tests** (`tests/unit/cli/setup/gitignore_negations/`):

- `test_ensure_root_gitignore_negations.py` — all scenarios (insert, idempotent, missing file, no .agdt/ rule)
- `test_ensure_root_gitignore_negations_integration.py` — integration-style test that initializes a temporary git repo, writes a
  `.gitignore` containing `.agdt/`, runs the helper, and then shells out to `git check-ignore` to confirm
  `.agdt/config/project.json` is actually unignored under real gitignore semantics

### Phase 3: Integrate into setup_cmd()

**Deliverable**: Modified `agentic_devtools/cli/setup/commands.py`

**Tasks**:

1. Add `--force-old-version` argparse argument (store_true, default False)
2. Move `git_root = _get_git_repo_root()` earlier — immediately after argparse
3. Insert version guard call after git_root detection:

   ```python
   guard_result = check_version_guard(git_root, args.force_old_version)
   if guard_result == "block":
       sys.exit(1)
   skip_repo_steps = (guard_result == "force")
   ```

4. When `skip_repo_steps` is True:
   - Local-only steps (cert prefetch, installs, dep check, env persist) still run
   - `_run_file_modifying_steps()` is NOT called
   - PR workflow is NOT invoked
5. Add `ensure_root_gitignore_negations(git_root)` call inside `_run_file_modifying_steps()` after `ensure_agdt_gitignore()`
6. Update or remove the existing `agdt-setup` console guidance that tells users to manually add `!.agdt/.gitignore` when the
   root `.gitignore` ignores `.agdt/`. Since the new `ensure_root_gitignore_negations()` handles negation rules automatically,
   this message is now outdated and would confuse users.
7. Add version pin write as the LAST step inside `_run_file_modifying_steps()`:

   ```python
   from agentic_devtools import __version__
   from agentic_devtools.cli.config.project_config import load_project_config, save_project_config
   config = load_project_config()
   config["agdt_version"] = __version__
   save_project_config(config)
   ```

**Tests** (`tests/unit/cli/setup/commands/`):

- Update `test_setup_cmd.py` with new scenarios for version guard integration:
  - **Fail-fast (older, no force)**: Mock `check_version_guard` to return `"block"` → assert `sys.exit(1)` is called,
    assert `_run_file_modifying_steps` is NOT called, assert local-only steps (cert prefetch, managed installs,
    dependency check, env persist) are NOT called
  - **Force-skip (older + `--force-old-version`)**: Mock `check_version_guard` to return `"force"` → assert exit code 0,
    assert local-only steps ARE called, assert `_run_file_modifying_steps()` is NOT called,
    assert PR workflow is NOT invoked
  - **Pass-through (equal/newer version)**: Mock `check_version_guard` to return `None` → assert exit code 0, assert both local-only steps AND `_run_file_modifying_steps()` are called normally
  - **`git_root` ordering**: Assert `_get_git_repo_root()` is called before `check_version_guard()` (verify call order via mock side effects)
  - **Flag interaction (`--force-old-version` + `--skip-pr-workflow`)**: When both flags are
    active, assert `--skip-pr-workflow` is still respected (PR workflow not invoked) and
    `--force-old-version` suppresses repo-modifying steps as expected — neither flag
    overrides the other
  - **Flag interaction (`--force-old-version` + `--system-only`)**: When both flags are
    active, assert `--system-only` behavior is preserved (only system-level steps run)
    and `--force-old-version` still suppresses repo-modifying steps — flag precedence
    is not accidentally changed by the refactor

### Phase 4: Final Validation

**Tasks**:

1. Run `bash scripts/run-pr-checks.sh` — all checks must pass
2. Verify `python scripts/validate_test_structure.py` passes
3. Manual smoke test of the four user stories

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Restructuring `setup_cmd()` breaks existing behavior | Medium | High | Comprehensive existing test coverage; run full suite before/after |
| `packaging` import fails in constrained environments | Low | Medium | NFR-003 fallback logic; fail-open behavior |
| Gitignore negation ordering wrong | Low | High | Integration test with `git check-ignore`; clear spec on ordering |
| PR workflow wrapping captures version write | Low | High | Version write is LAST inside `_run_file_modifying_steps()`; tested |
| Moving `git_root` detection earlier causes side effects | Low | Medium | `_get_git_repo_root()` is pure detection (no mutations) |

## Dependencies

- **Internal**: `agentic_devtools.cli.config.project_config` (load/save), `agentic_devtools.agdt_gitignore`, `agentic_devtools.__version__`
- **External**: `packaging>=21.0` (new explicit dependency)
- **Testing**: pytest, pytest-cov (existing dev deps)

---
*Generated by Copilot SDK (claude-opus-4.6)*
