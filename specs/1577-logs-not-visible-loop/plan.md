# Implementation Plan: AI PR Loop Orchestrator Log Visibility

## Technical Context

- **Language/Runtime**: Python 3.x (single-process, single-thread CLI tool)
- **Package**: `agentic_devtools` — pip-installable CLI with entry points in `pyproject.toml`
- **CI Platform**: GitHub Actions (logs to stderr, stdout reserved for JSON decision summaries)
- **Logging**: All 18+ CI modules already use `logging.getLogger(__name__)` but no handler is configured at the entry point
- **Entry Points**: `ai_pr_loop_command()` and `speckit_trigger_command()` in `agentic_devtools/cli/ci/commands.py`
- **Existing Group Helpers**: `_log_group()` / `_log_endgroup()` duplicated in `orchestrator.py` and `pipeline/runner.py` as module-private functions
- **Test Framework**: pytest with 1:1:1 test structure under `tests/unit/`

## Research Summary

See [research.md](research.md) for detailed decisions on:

- Logging handler placement and idempotency strategy
- Group annotation consolidation approach
- Subprocess output capture pattern

## Design Overview

```text
┌──────────────────────────────────────────────────────┐
│ commands.py (entry points)                           │
│   ai_pr_loop_command()  ──→ setup_logging()          │
│   speckit_trigger_command() ──→ setup_logging()      │
└──────────────────────┬───────────────────────────────┘
                       │ imports
                       ▼
┌──────────────────────────────────────────────────────┐
│ logging_config.py (NEW)                              │
│   setup_logging() — idempotent handler config        │
│   log_group() — context manager for ::group::        │
│   is_github_actions() — env check (consolidated)     │
└──────────────────────────────────────────────────────┘
                       │ used by
                       ▼
┌──────────────────────────────────────────────────────┐
│ orchestrator.py / pipeline/runner.py                 │
│   Replace _log_group/_log_endgroup with imports      │
│   from logging_config                                │
└──────────────────────────────────────────────────────┘
```

## Implementation Phases

### Phase 1: Create `logging_config.py` Module (Core — FR-001, FR-002, FR-006, FR-008)

**Deliverable**: New module `agentic_devtools/cli/ci/logging_config.py`

**Tasks**:

1. Create `agentic_devtools/cli/ci/logging_config.py` with:
   - `setup_logging()` — idempotent function that checks `logging.root.handlers`; if empty, adds a `StreamHandler(sys.stderr)` with format `%(asctime)s %(levelname)-8s %(name)s: %(message)s` and
     `datefmt="%H:%M:%S"`; reads `AGDT_LOG_LEVEL` env var, validates against known levels, warns on invalid values, defaults to INFO
   - `is_github_actions() -> bool` — returns `os.environ.get("GITHUB_ACTIONS") == "true"`
   - `log_group(title: str)` — context manager that emits `::group::{title}` on enter and `::endgroup::` on exit, only when `is_github_actions()` is True; otherwise no-op
2. Write tests: `tests/unit/cli/ci/logging_config/test_setup_logging.py`, `test_is_github_actions.py`, `test_log_group.py`

### Phase 2: Wire Entry Points (FR-001, FR-007)

**Deliverable**: Both CLI entry points call `setup_logging()` before any logic

**Tasks**:

1. In `commands.py` → `ai_pr_loop_command()`: add `from agentic_devtools.cli.ci.logging_config import setup_logging` and call `setup_logging()` as the first statement (before feature flag check)
2. In `commands.py` → `speckit_trigger_command()`: same pattern
3. Update existing tests in `tests/unit/cli/ci/commands/` to verify logging is configured (mock `setup_logging` or assert handler presence)

### Phase 3: Consolidate Group Helpers (FR-005, FR-008)

**Deliverable**: Remove duplicated `_log_group`/`_log_endgroup`/`_is_github_actions` from `orchestrator.py` and `pipeline/runner.py`; replace with imports from `logging_config.py`

**Tasks**:

1. In `orchestrator.py`: remove `_is_github_actions()`, `_log_group()`, `_log_endgroup()`; import `is_github_actions`, `log_group` from `logging_config`; update usages (note: `_emit_decision_summary`
   uses group/endgroup — convert to context manager)
2. In `pipeline/runner.py`: same removal and import replacement
3. Update any tests that mock the removed private functions

### Phase 4: Ensure Critical Logs Are Outside Groups (FR-003, FR-004)

**Deliverable**: Guard decisions and action outcomes are logged at INFO level outside collapsed groups

**Tasks**:

1. Audit `guards.py` — verify guard block/allow outcomes use `logger.info()` (they already do per existing `getLogger` usage; confirm no group wrapping)
2. Audit `pipeline/actions/*.py` — verify action outcomes (merge result, repair dispatch, approval) use `logger.info()` outside groups
3. Ensure verbose payloads (JSON dumps, API responses) are logged at DEBUG level or wrapped in `log_group()` context manager
4. Add/adjust log statements where FR-003/FR-004 are not yet satisfied

### Phase 5: Subprocess Output Handling (Edge Case)

**Deliverable**: Subprocess stderr captured and re-emitted through logging

**Tasks**:

1. Identify `gh` CLI subprocess calls in CI modules (primarily in `github_provider.py`)
2. Ensure calls use `capture_output=True` and re-emit stderr:
   - On success (returncode 0): `logger.debug("gh stderr: %s", stderr)`
   - On failure (returncode != 0): `logger.warning("gh failed (exit %d): %s", code, stderr)`
3. Verify stdout is processed programmatically (already the case per existing code patterns)

### Phase 6: Tests & Validation

**Deliverable**: Full test coverage for new module, no regressions

**Tasks**:

1. Create all 1:1:1 test files for `logging_config.py` symbols
2. Run `agdt-test` to verify no regressions
3. Run `bash scripts/run-pr-checks.sh` for full CI validation
4. Validate locally: run `agdt-ai-pr-loop` with mock event → confirm ≥10 formatted log lines on stderr

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Duplicate log lines from multiple handler configurations | Medium | Low | Idempotency check on `logging.root.handlers` (explicit requirement) |
| Breaking existing tests that rely on captured output | Medium | Medium | Mock `setup_logging` in existing command tests; verify stderr vs stdout separation |
| `_emit_decision_summary` stdout output affected | Low | High | Decision summary uses `sys.stdout` directly — unaffected by stderr logging handler |
| Group annotation context manager not cleaning up on exception | Low | Medium | Use `try/finally` in context manager `__exit__` |
| Subprocess output capture changes break provider tests | Medium | Medium | Phase 5 changes are conservative; existing `capture_output=True` patterns preserved |

## Dependencies

- **Internal**: No new package dependencies; uses only Python stdlib `logging`, `os`, `sys`, `contextlib`
- **External**: None
- **Prerequisite**: No other PRs need to merge first
- **CI**: Existing GitHub Actions workflow `ai-pr-loop.yml` requires no changes (logs appear automatically once handler is configured)

---
*Generated by Copilot SDK (claude-opus-4.6)*
