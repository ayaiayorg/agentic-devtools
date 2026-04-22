# Implementation Plan: Remove `--yes` Flag & Change Default Merge Strategy to Rebase

## Technical Context

- **Language**: Python 3 (pip-installable CLI package)
- **Testing**: pytest with 1:1:1 test structure under `tests/unit/`
- **CI checks**: `bash scripts/run-pr-checks.sh` (pytest + ruff + markdownlint + mypy)
- **Source file**: `agentic_devtools/cli/github/pr_merge.py`
- **Tests likely to need updates**:
  - `tests/unit/cli/github/pr_merge/test__check_gh_available.py`
  - `tests/unit/cli/github/pr_merge/test__classify_merge_error.py`
  - `tests/unit/cli/github/pr_merge/test__execute_merge.py`
  - `tests/unit/cli/github/pr_merge/test__verify_merge.py`
  - `tests/unit/cli/github/pr_merge/test_merge_pr.py`
  - `tests/unit/cli/github/pr_merge/test_pr_merge_command.py`
- **Docs** (2):
  - `.github/copilot-instructions.md`
  - `.github/prompts/agdt.pr-merge-manager.prompt.md`

> **Mirror check**: `.github/agents/copilot-instructions.md` exists but contains no
> merge-strategy references — no update needed. No `custom-instructions/` directory
> exists in this repository.

## Research Summary

Key decisions from research:

1. **No replacement flag needed** — `gh pr merge --rebase` bypasses interactive confirmation without `--yes`.
2. **No backward-compat concern** — the command was completely broken, so there is no working behaviour to preserve.
3. **Consistent multi-location update required** — change the default in `_DEFAULT_STRATEGY`, the `merge_pr()` function signature, and argparse so they stay aligned.

## Design Overview

This is a surgical bug-fix + default-change. The architecture is unchanged — only values are modified.

```text
pr_merge.py
├── _DEFAULT_STRATEGY = "squash" → "rebase"        (constant)
├── _execute_merge()  → remove "--yes" from cmd     (bug fix)
├── merge_pr()        → strategy="squash" → _DEFAULT_STRATEGY (signature)
└── pr_merge_command() → help text updated           (argparse)
```

## Implementation Phases

### Phase 1 — Bug Fix: Remove `--yes` (FR-001)

**Source change** — `agentic_devtools/cli/github/pr_merge.py` line 73:

```python
# Before
cmd = ["gh", "pr", "merge", str(pr_number), "--repo", repo, f"--{strategy}", "--yes"]
# After
cmd = ["gh", "pr", "merge", str(pr_number), "--repo", repo, f"--{strategy}"]
```

**Test update** — `test__execute_merge.py` line 22:

```python
# Before
assert "--yes" in cmd
# After
assert "--yes" not in cmd
```

**Deliverable**: `_execute_merge` no longer emits `--yes`; test asserts its absence.

### Phase 2 — Default Change: Squash → Rebase (FR-002, FR-003, FR-004)

**Source changes** — `agentic_devtools/cli/github/pr_merge.py`:

| Line | Before | After |
|------|--------|-------|
| 22 | `_DEFAULT_STRATEGY = "squash"` | `_DEFAULT_STRATEGY = "rebase"` |
| 120 | `strategy: str = "squash"` | `strategy: str = _DEFAULT_STRATEGY` |
| 286 | `help="Merge strategy (default: squash)"` | `help="Merge strategy (default: rebase)"` |

**Test updates** — `test_merge_pr.py`:

| Line | Before | After |
|------|--------|-------|
| 34 | `("github.pr_merge_strategy", "squash")` | `("github.pr_merge_strategy", "rebase")` |
| 151 | `("github.pr_merge_strategy", "squash")` | `("github.pr_merge_strategy", "rebase")` |
| 153 | `test_default_strategy_is_squash` | `test_default_strategy_is_rebase` |
| 167 | `assert mock_exec.call_args[0][2] == "squash"` | `assert mock_exec.call_args[0][2] == "rebase"` |

**Test updates** — `test_pr_merge_command.py`:

| Line | Before | After |
|------|--------|-------|
| 25 | `mock_merge.assert_called_once_with(42, "o/r", "squash", True)` | `mock_merge.assert_called_once_with(42, "o/r", "rebase", True)` |
| 42 | `mock_merge.assert_called_once_with(99, "o/r", "squash", True)` | `mock_merge.assert_called_once_with(99, "o/r", "rebase", True)` |
| 68 | `mock_merge.assert_called_once_with(42, "o/r", "squash", False)` | `mock_merge.assert_called_once_with(42, "o/r", "rebase", False)` |
| 121 | `mock_merge.assert_called_once_with(42, "o/r", "squash", True)` | `mock_merge.assert_called_once_with(42, "o/r", "rebase", True)` |

**Deliverable**: Default strategy is `"rebase"` everywhere; all tests updated.

### Phase 3 — Documentation Updates (FR-004 docs)

**`.github/copilot-instructions.md`** — 2 edits:

1. Line 160: `gh pr merge --squash --delete-branch` → `gh pr merge --rebase --delete-branch`
2. Line 180: `default squash` → `default rebase`

**`.github/prompts/agdt.pr-merge-manager.prompt.md`** — 1 edit:

1. Line 21: `` `gh pr merge --squash` + verification `` → `` `gh pr merge --rebase` + verification ``

**Deliverable**: All docs say `rebase` as default.

### Phase 4 — Validation

1. Run `agdt-test-pattern tests/unit/cli/github/pr_merge/ -v` — all tests pass
2. Run `bash scripts/run-pr-checks.sh` — full CI suite green
3. Grep for stale `--yes` references: `grep -r '"--yes"' agentic_devtools/` — zero hits
4. Grep for stale squash defaults: `grep -rn 'default squash\|default: squash\|_DEFAULT_STRATEGY.*squash\|strategy.*=.*"squash"' agentic_devtools/cli/github/pr_merge.py` — zero hits

**Deliverable**: All success criteria (SC-001 through SC-005) verified.

## Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Missed `--yes` reference elsewhere | Low | Very Low | Codebase grep confirms single occurrence (line 73) |
| Missed squash default in another file | Low | Very Low | Grep across repo; only `pr_merge.py` has the constant |
| Breaking existing explicit `--strategy squash` usage | None | None | Explicit strategies are unaffected (FR-005) |
| `--no-delete-branch` regression | None | None | Orthogonal flag; not touched |

## Dependencies

- **Internal**: No new module dependencies
- **External**: No new package dependencies (NFR-002)
- **Tooling**: Existing `gh` CLI (no version change needed)

## Task Summary

| # | Task | File(s) | Phase |
|---|------|---------|-------|
| 1 | Remove `"--yes"` from `_execute_merge` cmd list | `pr_merge.py:73` | 1 |
| 2 | Update test to assert `--yes` absent | `test__execute_merge.py:22` | 1 |
| 3 | Change `_DEFAULT_STRATEGY` to `"rebase"` | `pr_merge.py:22` | 2 |
| 4 | Change `merge_pr` default param to `_DEFAULT_STRATEGY` | `pr_merge.py:120` | 2 |
| 5 | Update argparse help text to say `rebase` | `pr_merge.py:286` | 2 |
| 6 | Update `test_merge_pr.py` strategy assertions | `test_merge_pr.py:34,151,153,167` | 2 |
| 7 | Update `test_pr_merge_command.py` strategy assertions | `test_pr_merge_command.py:25,42,68,121` | 2 |
| 8 | Update copilot-instructions.md (2 lines) | `.github/copilot-instructions.md:160,180` | 3 |
| 9 | Update pr-merge-manager prompt (1 line) | `.github/prompts/agdt.pr-merge-manager.prompt.md:21` | 3 |
| 10 | Run full test suite + PR checks | — | 4 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
