# Implementation Plan: Dedicated commit-body.md for Commit Body

## Tracked Artifacts

The following artifacts are committed to this branch under `specs/1831-dedicated-commit-body-commit/`:

| Artifact | Status |
|----------|--------|
| `plan.md` | Tracked (this file) |
| `spec.md` | Tracked |
| `checklists/` | Tracked (directory) |
| `contracts/` | Tracked (directory) |

> **Note:** The PR description may reference additional optional artifacts (`data-model.md`,
> `quickstart.md`, `research.md`) that are **not** present in this branch. Those files are
> gitignored and only produced locally during spec generation. Only the artifacts listed above are
> committed and reviewable in-branch.

## 1. Technical Context

| Aspect | Detail |
|--------|--------|
| Language | Python 3.10+ |
| Package | `agentic_devtools` (pip-installable, entry points via `pyproject.toml`) |
| CLI routing | Most `agdt-*` commands route via `run_as_script` and `COMMAND_MAP` dispatch. Exception: `agdt-mcp-server` routes to `agentic_devtools.mcp.server:main` directly |
| Git commit mechanism | `commit_message` state key → `temp_message_file()` → `git commit -F <path>` |
| State directory | `.agdt/workflows/{identity}/{worktree_key}/` (resolved by `get_state_dir()`) |
| YAML parsing | `PyYAML>=6.0.0` already in `pyproject.toml` dependencies |
| Test policy | 1:1:1 test structure under `tests/unit/`, 100% branch coverage |
| Background tasks | `agdt-git-save-work` runs via `commit_async` (background task wrapper around `commit_cmd`) |

### Key Architecture Decisions

- The commit body file lives at `{state_dir}/files/commit-body.md` — inside the already-gitignored worktree state directory
- Body reading uses composable helper functions in a new `commit_body.py` module under `cli/git/`;
  `read_commit_body()` returns a structured absent-body result for missing, empty, and
  whitespace-only files, and is the single enforcement point for >100KB / UTF-8 hard
  failures so both CLI commands surface the same stderr text and non-zero exits
- The `commit_cmd()` function in `commands.py` is the single integration point where body injection occurs
- The `agdt-commit-body-show` command is a **synchronous** command (no background task needed — it only reads a file)

## 2. Research Summary

Key decisions informing this implementation:

- File location within state directory (`files/` subdirectory): placed inside the already-gitignored worktree state directory so no `.gitignore` entry is needed
- Frontmatter parsing approach: `PyYAML` `safe_load` (already a project dependency); malformed or non-mapping YAML triggers a warning and treats the entire file as body to avoid data loss
- Message assembly strategy: extract first line as title, append blank line, then body text
- BOM handling strategy: strip UTF-8 BOM before any processing
- Show command output format: structured header + frontmatter section + body section (see Phase 2)

## 3. Design Overview

```text
┌──────────────────────────────────────────────────────────────┐
│  agdt-git-save-work (commands.py::commit_cmd)                │
│                                                              │
│  1. message = get_commit_message()         ← state key      │
│  2. body = read_commit_body().body          ← NEW            │
│  3. if body.strip():                                         │
│       final_message = extract_title(message) + "\n\n" + body │
│     else:                                                    │
│       final_message = message              ← backward compat │
│  4. create_commit(final_message, dry_run)                    │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  agdt-commit-body-show (commit_body.py::show_cmd)            │
│                                                              │
│  1. body_result = read_commit_body()                         │
│  2. If file missing or a hard failure occurs: stderr + exit 1│
│  3. Otherwise print structured output to stdout              │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  commit_body.py (new module: agentic_devtools/cli/git/)      │
│                                                              │
│  Functions:                                                   │
│  - get_commit_body_path() → Path                             │
│  - read_commit_body() → CommitBodyResult                     │
│  - parse_frontmatter(content: str) → (dict, str)            │
│  - extract_title(message: str) → str                         │
│  - assemble_message(title: str, body: str) → str            │
│  - show_cmd() → None                                         │
└──────────────────────────────────────────────────────────────┘
```

## 4. Implementation Phases

### Phase 1: Core Module — `commit_body.py` (TDD)

**Deliverable**: New module `agentic_devtools/cli/git/commit_body.py` with composable helper
functions. Data-transformation helpers (`parse_frontmatter`, `extract_title`, `assemble_message`)
are side-effect-free, while `read_commit_body()` handles absent-body detection plus shared
warnings / hard-failure results and `show_cmd()` emits the required structured stdout output.

| Step | Action |
|------|--------|
| 1.1 | Create `tests/unit/cli/git/commit_body/` directory with `__init__.py` |
| 1.2 | Write failing tests for `get_commit_body_path()` — returns `{state_dir}/files/commit-body.md` |
| 1.3 | Write failing tests for `read_commit_body()` — covers: file missing, empty, whitespace-only, valid content, >100KB, non-UTF-8, BOM stripping, **parent `files/` directory missing** (treated as absent body — same non-error result as missing `commit-body.md`, satisfying FR-006) |
| 1.4 | Write failing tests for `parse_frontmatter()` — covers: no frontmatter, valid YAML, malformed YAML, YAML returning `None`, YAML returning non-dict; `None` is treated as `{}` and still strips the entire frontmatter block (including both `---` delimiters) so the body begins after the closing delimiter, while malformed/non-dict emits warning and preserves entire file content as body to prevent data loss |
| 1.5 | Write failing tests for `extract_title()` — covers: single line, multiline (only first line returned) |
| 1.6 | Write failing tests for `assemble_message()` — title + blank line + body |
| 1.7 | Implement all functions to pass tests |

**Key implementation details**:

```python
# commit_body.py key types
@dataclass
class CommitBodyResult:
    body: str              # Body text (empty string if absent)
    frontmatter: dict      # Parsed YAML frontmatter (empty dict if none)
    path: Path             # Resolved file path
    file_exists: bool      # Whether commit-body.md exists on disk, even if body is empty

MAX_BODY_FILE_SIZE = 102_400  # 100KB hard limit
COMMIT_BODY_FILENAME = "commit-body.md"
FILES_SUBDIR = "files"
```

Callers derive "has body" from `body.strip()` rather than from `file_exists`, while
continuing to pass the original `body` string unchanged for output / injection so
formatting is preserved. This lets `show_cmd()` distinguish a missing file (error)
from an existing-but-empty file (success with an empty/absent body).

### Phase 2: Show Command — `agdt-commit-body-show`

**Deliverable**: Working CLI command registered in `pyproject.toml` and `runner.py`.

| Step | Action |
|------|--------|
| 2.1 | Write failing tests for `show_cmd()` — covers: file present (with/without frontmatter), file missing (stderr + exit 1), file >100KB (stderr + exit 1), **malformed/non-mapping YAML frontmatter** (emits warning to stderr, prints entire file content as body with no parsed frontmatter section, satisfying FR-007 — prevents silent data loss or misleading "frontmatter parsed" output) |
| 2.2 | Implement `show_cmd()` in `commit_body.py` |
| 2.3 | Add entry point to `pyproject.toml`: `agdt-commit-body-show = "agentic_devtools.cli.runner:run_as_script"` |
| 2.4 | Add to `COMMAND_MAP` in `runner.py`: `"agdt-commit-body-show": ("agentic_devtools.cli.git.commit_body", "show_cmd")` |
| 2.5 | Export from `cli/git/__init__.py` |

**Show command output format**:

```text
══════════════════════════════════════════════════════════════════
COMMIT BODY: /path/to/.agdt/workflows/.../files/commit-body.md
Length: 1,234 characters
Frontmatter: yes (3 keys)
══════════════════════════════════════════════════════════════════

--- Frontmatter ---
checklist_items_completed: [1, 2, 3]
review_status: approved
issue_refs: ['#42']

--- Body ---
## Summary of changes

- Implemented webhook handler
- Added comprehensive unit tests
...
```

### Phase 3: Integration into `commit_cmd()`

**Deliverable**: `agdt-git-save-work` reads `commit-body.md` and injects body.

| Step | Action |
|------|--------|
| 3.1 | Write failing integration tests in `tests/unit/cli/git/commands/test_commit_cmd.py` — new test cases for body injection, title-only extraction, empty body fallback, >100KB abort |
| 3.2 | Modify `commit_cmd()` in `commands.py` to call `read_commit_body()` after getting the message and consume its shared result / hard-failure behavior |
| 3.3 | When `body_result.body.strip()` is non-empty: `message = assemble_message(extract_title(message), body_result.body)` |
| 3.4 | Missing / empty / whitespace-only files fall back to the existing `commit_message`; >100KB and UTF-8 decode failures are enforced by `read_commit_body()` so `agdt-git-save-work` and `agdt-commit-body-show` share the same error text |
| 3.5 | Verify all existing tests still pass unchanged (SC-001) |

**Integration point in `commands.py`** (after line 231):

```python
# Get commit message (CLI arg overrides state)
if args.commit_message:
    message = args.commit_message
else:
    message = get_commit_message()

# NEW: Read commit body from file (if present, overrides inline body)
from .commit_body import read_commit_body, extract_title, assemble_message
body_result = read_commit_body()
body = body_result.body
if body.strip():
    message = assemble_message(extract_title(message), body)
```

### Phase 4: Documentation Update

**Deliverable**: Updated copilot-instructions.md and module docstrings.

| Step | Action |
|------|--------|
| 4.1 | Add `commit-body.md` section to `.github/copilot-instructions.md` |
| 4.2 | Add `agdt-commit-body-show` to the command tables in the instructions |
| 4.3 | Update the "Initial Git Commit & Publish" workflow example to mention `commit-body.md` |
| 4.4 | Add module-level docstring to `commit_body.py` |

### Phase 5: Validation & CI

| Step | Action |
|------|--------|
| 5.1 | Run `python scripts/validate_test_structure.py` — ensure 1:1:1 compliance |
| 5.2 | Run `agdt-test` — full suite passes |
| 5.3 | Run `agdt-test-pattern "tests/unit/cli/git/commit_body/"` — validate new 1:1:1 test module |
| 5.4 | Run `bash scripts/targeted-checks.sh` — ruff, mypy, markdownlint all pass |
| 5.5 | Verify `agdt-commit-body-show` works end-to-end (manual smoke test) |

## 5. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Breaking existing tests that rely on `commit_message` full-value behavior | Low | High | Phase 3 explicitly preserves backward compat when no `commit-body.md` exists; all existing tests remain unchanged |
| BOM handling edge cases on Windows | Low | Medium | Explicit BOM stripping before any processing; tested with BOM fixture |
| Race condition: file deleted between size check and read | Very Low | Low | Use `stat().st_size` precheck for fast rejection and catch read-time filesystem errors defensively before parsing |
| Large files causing OOM | Very Low | Low | Enforce `stat().st_size <= 100KB` (or bounded read of MAX+1 bytes) before full decode/allocation |
| Frontmatter parser accepting dangerous YAML | Low | High | `yaml.safe_load` only — no arbitrary object construction |

## 6. Dependencies

### Internal Dependencies

| Dependency | Used For |
|------------|----------|
| `agentic_devtools.state.get_state_dir()` | Resolving the `files/commit-body.md` path |
| `agentic_devtools.cli.git.core.get_commit_message()` | Getting the title from state |
| `agentic_devtools.cli.git.commands.commit_cmd()` | Integration point for body injection |
| `agentic_devtools.cli.runner.COMMAND_MAP` | Registering the new show command |

### External Dependencies

| Dependency | Version | Already Present | Used For |
|------------|---------|-----------------|----------|
| PyYAML | >=6.0.0 | ✅ Yes | `yaml.safe_load` for frontmatter parsing |

No new dependencies required (satisfies NFR-004 and SC-005).

---
*Generated by Copilot SDK (claude-opus-4.6)*
