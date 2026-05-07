# Implementation Plan: Restructure setup-dev-tools into modular .agdt-managed scripts

**Issue**: [#1322](https://github.com/ayaiayorg/agentic-devtools/issues/1322)

## Technical Context

- **Language**: Python 3.10+, stdlib-only for generated scripts (no agentic-devtools imports in `.agdt/` scripts)
- **Package**: `agentic-devtools` — pip-installable CLI package with entry points via `pyproject.toml`
- **Existing setup**: `agdt-setup` command in `agentic_devtools/cli/setup/commands.py` handles dependency checking, CLI installs, cert prefetching, platform detection, skill injection, and workflow
  templates
- **State management**: `.agdt/` directory is currently fully gitignored (used for runtime state)
- **Entry point routing**: Most CLI entry points route through `agentic_devtools.cli.runner:run_as_script` (exception: `agdt-mcp-server` is wired directly to `agentic_devtools.mcp.server:main`)
- **Test structure**: 1:1:1 policy under `tests/unit/`, enforced by `scripts/validate_test_structure.py`

## Research Summary

See [research.md](research.md) for detailed decisions on:

- Atomic file writes for concurrency safety
- Site-packages corruption detection strategy
- Script generation template approach
- `.gitignore` modification strategy

## Design Overview

```text
┌─────────────────────────────────────────────────────────────────┐
│  agdt-setup (existing command, extended with new final phase)    │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Phase 1: Existing (deps, CLI installs, certs, config)      │ │
│  │ Phase 2: NEW — Script generation & .gitignore update       │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                           ↓ generates
┌─────────────────────────────────────────────────────────────────┐
│  setup-dev-tools.py (repo root, orchestrator)                   │
│  # AGDT-MANAGED-ORCHESTRATOR                                    │
│  → calls .agdt/agentic-devtools-complete-setup.py               │
│  → calls setup-repo-specific-dev-tools.py                       │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│  .agdt/agentic-devtools-complete-setup.py                       │
│  → calls .agdt/agentic-devtools-required-setup.py               │
│  → calls .agdt/agentic-devtools-configured-setup.py             │
└─────────────────────────────────────────────────────────────────┘
```

## Implementation Phases

### Phase 1: Core Self-Repair Script (`agentic-devtools-required-setup.py`)

**Deliverable**: A standalone Python script that detects and repairs corrupted installations.

1. Create `agentic_devtools/cli/setup/script_generators/` package
2. Create `agentic_devtools/cli/setup/script_generators/__init__.py`
3. Create `agentic_devtools/cli/setup/script_generators/required_setup.py` — generates the required-setup script content
4. Implement corruption detection logic:
   - Scan site-packages for `~gentic-devtools`, `~gentic_devtools` directories
   - Detect `.dist-info` directories without RECORD files
   - Detect `_editable_impl_agentic_devtools.pth` files
5. Implement cleanup logic with permission error handling
6. Implement `sys.executable -m pip install --upgrade agentic-devtools`
7. Implement git hooks setup (`core.hooksPath` → `.githooks`)
8. Handle edge cases: read-only site-packages, non-git contexts
9. Support `--foreground` flag (no-op today, forward-compatible)

### Phase 2: Configured Setup Generator

**Deliverable**: Script generation based on user tool selections.

1. Create `agentic_devtools/cli/setup/script_generators/configured_setup.py`
2. Define tool registry (cspell, ruff, markdownlint-cli2, etc.)
3. Implement template rendering for configured-setup script based on selected tools
4. Ensure generated scripts use only stdlib modules
5. Ensure idempotent output (NFR-003)

### Phase 3: Orchestrator Scripts

**Deliverable**: Complete-setup and root entry-point scripts.

1. Create `agentic_devtools/cli/setup/script_generators/complete_setup.py` — generates the complete-setup orchestrator
2. Create `agentic_devtools/cli/setup/script_generators/root_entry_point.py` — generates `setup-dev-tools.py`
3. Implement fail-fast subprocess orchestration pattern
4. Add `# AGDT-MANAGED-ORCHESTRATOR` marker to generated root script
5. Implement `--foreground` flag propagation
6. Handle missing `.agdt/` directory with clear error message

### Phase 4: Legacy Migration & `agdt-setup` Integration

**Deliverable**: Extend `agdt-setup` with script generation phase.

1. Create `agentic_devtools/cli/setup/script_generators/repo_specific.py` — generates the stub customer script
2. Implement legacy detection (check for `# AGDT-MANAGED-ORCHESTRATOR` marker absence)
3. Implement legacy content migration to `setup-repo-specific-dev-tools.py`:
   - If target doesn't exist: move content verbatim
   - If target exists: append below separator comment
4. Add new phase at the end of `setup_cmd()` in `commands.py`
5. Implement atomic file writes (write to temp, then rename) for concurrency safety
6. Wire up tool selection prompts to configured-setup generation

### Phase 5: `.gitignore` Update

**Deliverable**: Managed scripts trackable by git.

1. Create `agentic_devtools/cli/setup/script_generators/gitignore_updater.py`
2. Replace `.agdt/` rule with `.agdt/*` in root `.gitignore`
3. Add `!.agdt/agentic-devtools-*.py` negation rule
4. Ensure idempotent application (don't duplicate rules on re-run)
5. Integrate into the `agdt-setup` script generation phase

### Phase 6: Testing

**Deliverable**: Full test coverage for all new modules.

1. Unit tests for corruption detection logic
2. Unit tests for script content generation (verify output is stdlib-only, contains expected patterns)
3. Unit tests for legacy migration logic
4. Unit tests for `.gitignore` modification
5. Unit tests for orchestrator fail-fast behavior
6. Integration tests simulating full `agdt-setup` flow with mocked filesystem
7. Edge case tests: read-only site-packages, non-git context, concurrent runs, missing `.agdt/`

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Generated scripts break on Windows due to path separators | High | Use `pathlib.Path` and `os.path` exclusively; test on Windows CI |
| Corruption detection false positives remove valid packages | Critical | Conservative pattern matching; only target known artifact patterns |
| `.gitignore` modification corrupts existing rules | Medium | Parse and modify surgically; validate before writing |
| Legacy migration loses customer code | High | Never overwrite existing `setup-repo-specific-dev-tools.py`; append with separator |
| Atomic writes fail on network filesystems | Low | Fall back to direct write with fsync; document limitation |

## Dependencies

- **Internal**: Repo-root detection — implementation should use a public helper
  (e.g., a new `get_git_repo_root()` in `agentic_devtools.cli.setup.utils`) or keep
  detection logic local to the setup module, rather than coupling to the private
  `agentic_devtools.state._get_git_repo_root()`
- **Internal**: `agentic_devtools.cli.setup.commands.setup_cmd()` as integration point
- **External**: `pip` (invoked via `sys.executable -m pip`) for package installation
- **External**: `git` CLI for hooks configuration
- **None**: Generated scripts must have zero external dependencies (stdlib only)

---
*Generated by Copilot SDK (claude-opus-4.6)*
