# Implementation Plan: Persist Commit Params and Rendered Messages to State

## 1. Technical Context

- **Language/Framework**: Python 3, pip-installable package (`agentic_devtools`)
- **Key Files**:
  - `agentic_devtools/cli/git/commands.py` — `commit_cmd()` orchestrator (primary change target)
  - `agentic_devtools/cli/git/core.py` — `get_commit_message()` utility
  - `agentic_devtools/state.py` — `read_modify_write_state()` context manager for atomic state updates
  - `agentic_devtools/cli/git/operations.py` — `create_commit()` / `amend_commit()` (unchanged)
- **Testing**: pytest with 100% branch coverage, 1:1:1 test structure under `tests/unit/`
- **State**: JSON file at `.agdt/workflows/{identity}/{worktree_key}/state.json`
- **Concurrency**: `read_modify_write_state()` provides exclusive-lock read/modify/write

## 2. Research Summary

See [research.md](research.md) for detailed analysis of:

- Atomic state write approach (decision: `read_modify_write_state()`)
- Commit message fallback placement (decision: in `commit_cmd()` before `get_commit_message()`)
- Title extraction strategy (decision: split on first `\n`)

## 3. Design Overview

```text
commit_cmd()
  │
  ├─ [NEW] Fallback: if no --commit-message and commit_message state is empty,
  │        read git.last_commit_message from state as default
  │
  ├─ get_commit_message() (unchanged — simple state reader)
  │
  ├─ create_commit() / amend_commit()  ──── returns (no exception = success)
  │
  ├─ [NEW] _persist_commit_metadata(message)
  │        └─ read_modify_write_state():
  │             - commit_message_title = title
  │             - git.last_commit_title = title
  │             - git.last_commit_message = message
  │             - git.last_commit_body = body
  │
  ├─ _sync_with_main()
  └─ push / force_push / publish
```

Key design principles:

1. **Persistence after commit, before push** — commit exists locally even if push fails
2. **No persistence on dry-run or failure** — `create_commit()`/`amend_commit()` call `sys.exit()` on failure, so if we reach the persistence call, the commit succeeded
3. **All-or-nothing via `read_modify_write_state()`** — single locked write for all 4 keys
4. **Fallback is opt-in** — only fires when both CLI arg and `commit_message` state are empty

## 4. Implementation Phases

### Phase 1: Helper Function — `_extract_commit_parts()`

**Deliverable**: A pure function that splits a commit message into title and body.

**Location**: `agentic_devtools/cli/git/commands.py` (private helper)

```python
def _extract_commit_parts(message: str) -> tuple[str, str]:
    """Extract title and body from a commit message.

    Returns:
        (title, body) where body excludes the leading blank separator line.
        Body is "" if the message is title-only.
    """
```

**Logic**:

- Split on first `\n` → title is everything before
- Body is everything after, with one leading blank line stripped (if present)
- Title-only messages → body = `""`

**Tests** (1:1:1 at `tests/unit/cli/git/commands/test__extract_commit_parts.py`):

- Title-only message
- Title + blank + body
- Title + blank + multi-line body with footer
- Title + body without blank separator (unusual but valid)
- Empty string edge case

---

### Phase 2: Persistence Function — `_persist_commit_metadata()`

**Deliverable**: Function that atomically writes all 4 state keys.

**Location**: `agentic_devtools/cli/git/commands.py` (private helper)

```python
def _persist_commit_metadata(message: str) -> None:
    """Persist commit message parts to state atomically."""
```

**Logic**:

1. Call `_extract_commit_parts(message)` → `(title, body)`
2. Use `read_modify_write_state()` as context manager
3. Set all 4 keys in the yielded dict:
   - `state["commit_message_title"] = title`
   - `state["git.last_commit_title"] = title`
   - `state["git.last_commit_message"] = message`
   - `state["git.last_commit_body"] = body`

**Tests** (`tests/unit/cli/git/commands/test__persist_commit_metadata.py`):

- Verifies all 4 keys are written correctly
- Verifies overwrite of existing values
- Verifies exact message preservation (whitespace, special chars)
- Verifies title-only produces empty body string

---

### Phase 3: Fallback Logic in `commit_cmd()`

**Deliverable**: Before calling `get_commit_message()`, check `git.last_commit_message` as fallback.

**Location**: Modify `commit_cmd()` in `commands.py`, lines ~227-231.

**Current code**:

```python
if args.commit_message:
    message = args.commit_message
else:
    message = get_commit_message()
```

**New code**:

```python
if args.commit_message:
    message = args.commit_message
else:
    # Check if commit_message state key has a value before calling
    # get_commit_message() which sys.exit(1) if empty.
    raw_msg = get_value("commit_message")
    if raw_msg:
        message = str(raw_msg)
    else:
        # Fallback: reuse last committed message (FR-001)
        last_msg = get_value("git.last_commit_message")
        if last_msg:
            message = str(last_msg)
            print("Using previously committed message (from git.last_commit_message)")
        else:
            # No fallback available — call get_commit_message() which will sys.exit(1)
            message = get_commit_message()
```

**Tests** (extend `tests/unit/cli/git/commands/test_commit_cmd.py`):

- Test fallback fires when `commit_message` is empty but `git.last_commit_message` exists
- Test fallback does NOT fire when `commit_message` is set
- Test fallback does NOT fire when `--commit-message` CLI arg is provided
- Test `sys.exit(1)` when both are empty

---

### Phase 4: Integrate Persistence into `commit_cmd()`

**Deliverable**: Call `_persist_commit_metadata()` after successful commit/amend, gated by `not dry_run`.

**Location**: `commit_cmd()`, after the commit/amend block (after line 257), before `_sync_with_main()`.

```python
    # Persist commit metadata to state (only on real commits)
    if not dry_run:
        _persist_commit_metadata(message)
```

**Tests** (extend `tests/unit/cli/git/commands/test_commit_cmd.py`):

- Verify state keys are populated after successful commit
- Verify state keys are NOT written during dry-run
- Verify state keys update on amend path
- Verify push failure does not prevent persistence (already guaranteed by ordering)

---

### Phase 5: Documentation Update

**Deliverable**: Add state keys to `.github/copilot-instructions.md`.

**Location**: Under "Git Workflow Actions (Background Tasks)" section, add new state keys table.

**Content to add**:

```markdown
**State keys written by `agdt-git-save-work`:**
`commit_message_title`, `git.last_commit_title`, `git.last_commit_message`, `git.last_commit_body`

**State key `git.last_commit_message` fallback:**
When no `--commit-message` CLI arg is passed and the `commit_message` state key is absent/empty,
`agdt-git-save-work` reuses `git.last_commit_message` as the default commit message.
```

---

### Phase 6: Validation & CI

1. Run `agdt-test` (full suite), then `agdt-task-wait` — verify zero regressions
2. Run `agdt-test-pattern tests/unit/cli/git/commands/` — verify all new tests pass
3. Run `python scripts/validate_test_structure.py` — verify 1:1:1 compliance
4. Run `bash scripts/targeted-checks.sh` — verify lint, format, mypy, coverage

## 5. Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| `create_commit()`/`amend_commit()` call `sys.exit()` on failure, so persistence code is unreachable on error | Low | N/A | This is the desired behavior — no mitigation needed |
| Lock contention with concurrent background tasks | Low | Low | `read_modify_write_state()` already handles this with timeout |
| `commit_message_title` collision with spec #1830 intent key | Medium | Medium | FR-009 explicitly declares it as output-only; spec #1830 must migrate to `create_commit_message_title` |
| Fallback reusing stale message after `agdt-clear` | Low | Low | `agdt-clear` removes all keys including `git.last_commit_message` |

## 6. Dependencies

- **Internal**: `agentic_devtools.state.read_modify_write_state` (exists, no changes needed)
- **Internal**: `agentic_devtools.state.get_value` (exists, used for fallback read)
- **External**: None — no new packages required
- **Spec dependency**: FR-009 notes that spec #1830 may need follow-on migration of `commit_message_title` to a dedicated input key

---
*Generated by Copilot SDK (claude-opus-4.6)*
