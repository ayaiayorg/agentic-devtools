# Implementation Plan: Split Create vs. Amend Commit Title Parameters & Transparency Logging

## 1. Technical Context

- **Language**: Python 3.10+
- **Package**: `agentic_devtools` (pip-installable CLI tool)
- **Key files**:
  - `agentic_devtools/cli/git/commands.py` — CLI entry points (`commit_cmd`, `amend_cmd`)
  - `agentic_devtools/cli/git/operations.py` — Git operations (`create_commit`, `amend_commit`, `should_amend_instead_of_commit`, `get_last_commit_message`)
  - `agentic_devtools/cli/git/core.py` — Low-level helpers (`get_commit_message`, `run_git`, `temp_message_file`)
- **Test framework**: pytest with 100% branch coverage requirement
- **Test structure**: 1:1:1 policy under `tests/unit/cli/git/`
- **CLI**: argparse-based entry points registered in `pyproject.toml`
- **State**: JSON state via `agentic_devtools.state.get_value()`/`set_value()`

## 2. Research Summary

See [research.md](research.md) for detailed decisions on:

- Message resolution logic (title + body composition)
- Conflict detection ordering
- Transparency logging format and placement
- Backward compatibility strategy

## 3. Design Overview

```text
┌─────────────────────────────────────────────────────────────┐
│                    commit_cmd() entry point                   │
├─────────────────────────────────────────────────────────────┤
│  1. Parse args (new: --commit-message-title,                │
│     --overwrite-commit-message-title)                        │
│  2. Resolve intent: create-new vs. overwrite vs. legacy     │
│  3. Validate conflicts (both signals present → exit 1)      │
│  4. Route to appropriate path                                │
├──────────────┬────────────────────────┬─────────────────────┤
│ CREATE PATH  │   OVERWRITE PATH       │   LEGACY PATH       │
│ (new title)  │   (amend title only)   │   (commit_message)  │
│              │                        │                     │
│ Validate:    │ Validate:              │ Heuristic:          │
│ no commits   │ has commits ahead      │ should_amend_*()    │
│ ahead        │                        │                     │
│              │                        │                     │
│ Resolve body │ Read existing body     │ Use full message    │
│ from legacy  │ Replace title only     │ as-is               │
│ sources      │                        │                     │
├──────────────┴────────────────────────┴─────────────────────┤
│           TRANSPARENCY LOGGING (all paths)                   │
│  • Print "--- Resolved Commit Message ---" block            │
│  • For amend: print before/after commit-title diff block    │
│    (full resolved commit message is logged separately)       │
├─────────────────────────────────────────────────────────────┤
│                   Execute git command                         │
└─────────────────────────────────────────────────────────────┘
```

## 4. Implementation Phases

### Phase 1: Transparency Logging Infrastructure (FR-004, FR-005)

**Deliverables**: Helper functions for canonical log output, including
before/after commit-title diffs on amend paths (the clarified spec narrows
this diff to titles, while the full resolved commit message is logged
separately).

**Files to create/modify**:

- `agentic_devtools/cli/git/transparency.py` (NEW) — logging helpers
- `tests/unit/cli/git/transparency/` (NEW) — tests for logging helpers

**Functions**:

```python
def print_resolved_commit_message(message: str) -> None:
    """Print the full resolved commit message in canonical format."""

def print_commit_title_change(old_title: str, new_title: str) -> None:
    """Print before/after commit title diff in canonical format."""
```

**Test files** (1:1:1 structure):

- `tests/unit/cli/git/transparency/__init__.py`
- `tests/unit/cli/git/transparency/test_print_resolved_commit_message.py`
- `tests/unit/cli/git/transparency/test_print_commit_title_change.py`

---

### Phase 2: Message Resolution Logic (FR-001, FR-002, FR-003)

**Deliverables**: Intent detection, conflict validation, body resolution.

**Files to create/modify**:

- `agentic_devtools/cli/git/commit_intent.py` (NEW) — intent resolution + validation
- `tests/unit/cli/git/commit_intent/` (NEW) — tests

**Key functions**:

```python
@dataclass
class CommitIntent:
    mode: Literal["create", "overwrite", "legacy"]
    title: str | None  # None for legacy mode
    body: str | None   # Resolved body (for create mode)
    full_message: str  # The fully resolved commit message

def resolve_commit_intent(
    cli_commit_message_title: str | None,
    cli_overwrite_commit_message_title: str | None,
    cli_commit_message: str | None,
    state_commit_message_title: str | None,
    state_overwrite_commit_message_title: str | None,
    state_commit_message: str | None,
) -> CommitIntent:
    """
    Resolve the commit intent from explicit CLI flag and state-key inputs.
    Exits with status 1 on conflicts or validation failures.
    """
```

**Validation order** (per FR-001/FR-002):

1. Detect conflicts (both create-intent and amend-intent present) → exit 1
2. For create: reject branches with commits ahead of main → exit 1
3. For create: resolve body from the selected legacy `commit_message` source → exit 1 only when neither CLI nor state provides `commit_message`
4. For overwrite: reject branches with NO commits ahead → exit 1

**Test files**:

- `tests/unit/cli/git/commit_intent/__init__.py`
- `tests/unit/cli/git/commit_intent/test_resolve_commit_intent.py`
- `tests/unit/cli/git/commit_intent/test_commitintent.py`

---

### Phase 3: Integrate New Params into `commit_cmd` (FR-001, FR-002, FR-006)

**Deliverables**: Updated `commit_cmd` with new CLI flags and routing.

**Files to modify**:

- `agentic_devtools/cli/git/commands.py` — add args, integrate intent resolution
- `agentic_devtools/cli/git/operations.py` — add transparency logging to `create_commit` and `amend_commit`

**Changes to `commit_cmd`**:

1. Add `--commit-message-title` and `--overwrite-commit-message-title` to argparse
2. Call `resolve_commit_intent()` to determine mode
3. Route to `create_commit` or `amend_commit` based on resolved intent
4. Legacy path (neither new flag present) remains unchanged

**Changes to `create_commit`**:

- Call `print_resolved_commit_message(message)` before executing git

**Changes to `amend_commit`**:

- Accept optional `old_title` parameter for commit-title diff logging
- Call `print_commit_title_change(old_title, new_title)` before amend
- Call `print_resolved_commit_message(message)` before executing git

**Test updates**:

- `tests/unit/cli/git/commands/test_commit_cmd.py` — new test cases for new flags
- `tests/unit/cli/git/operations/test_create_commit.py` — verify logging output
- `tests/unit/cli/git/operations/test_amend_commit.py` — verify logging output

---

### Phase 4: Update `amend_cmd` (FR-007)

**Deliverables**: `agdt-git-amend` adopts transparency logging.

**Files to modify**:

- `agentic_devtools/cli/git/commands.py` — update `amend_cmd` / `_do_amend`

**Changes**:

- Before calling `amend_commit`, read the old title from the existing commit
  message returned by `get_last_commit_message()`
- Print the commit-title diff and resolved message

**Test updates**:

- `tests/unit/cli/git/commands/test_amend_cmd.py` — verify transparency output

---

### Phase 5: State Keys & Documentation (FR-003, FR-008, NFR-003)

**Deliverables**: State key support, updated docstrings, instruction docs.

**Files to modify**:

- `agentic_devtools/cli/git/core.py` — add state key constants
- `agentic_devtools/cli/git/commands.py` — update docstrings for `commit_cmd` and `amend_cmd`
- `.github/copilot-instructions.md` — update agent docs

**State key constants to add to `core.py`**:

```python
STATE_COMMIT_MESSAGE_TITLE = "commit_message_title"
STATE_OVERWRITE_COMMIT_MESSAGE_TITLE = "overwrite_commit_message_title"
```

---

### Phase 6: Final Validation & Coverage

**Deliverables**: Full test suite passing, 100% coverage on modified files.

**Actions**:

1. Run `agdt-test` followed by `agdt-task-wait` to verify full suite passes
2. Run `agdt-test-pattern tests/unit/cli/git/commands/ -v`
3. Run `agdt-test-pattern tests/unit/cli/git/operations/ -v`
4. Run `agdt-test-pattern tests/unit/cli/git/transparency/ -v`
5. Run `agdt-test-pattern tests/unit/cli/git/commit_intent/ -v`
6. Run `bash scripts/targeted-checks.sh` for lint/format/mypy
7. Verify markdownlint on modified docs

## 5. Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing `commit_message` workflows | High | Legacy path is untouched when new flags absent; existing tests must pass unmodified |
| Conflict detection edge cases (mixed CLI + state) | Medium | Exhaustive test matrix for all conflict combinations |
| Body resolution from `commit_message` with only title line | Low | Explicit handling: empty body is valid |
| `get_last_commit_message()` returns None during overwrite | Medium | Validate commits ahead before attempting to read old title |
| Transparency output interfering with parseable output | Low | Use canonical delimiter format that's machine-parseable |

## 6. Dependencies

**Internal**:

- `agentic_devtools.state.get_value()` — read state keys
- `agentic_devtools.cli.git.operations.branch_has_commits_ahead_of_main()` — validation
- `agentic_devtools.cli.git.operations.get_last_commit_message()` — old title for diffs
- `agentic_devtools.cli.git.core.temp_message_file()` — commit message writing

**External**:

- `git` CLI (already required)
- No new Python package dependencies

---
*Generated by Copilot SDK (claude-opus-4.6)*
