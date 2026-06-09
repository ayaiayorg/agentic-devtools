# Implementation Plan: PR Body Template with Commit Aggregation Fallback

## 1. Technical Context

**Technology Stack:**

- Python >=3.10 package (`agentic-devtools`) installed via pip/pipx
- CLI entry points registered in `pyproject.toml` via `[project.scripts]`
- State management via JSON file (`.agdt/workflows/{identity}/{worktree_key}/state.json`)
- Template interpolation using `{{variable}}` placeholder replacement (`str.replace()` in shared utility)
- Background task execution via `run_in_background()` / `run_function_in_background()`
- Platform targets: Azure DevOps (`az repos pr create`) and GitHub (`gh pr create`)

**Key Dependencies:**

- `agentic_devtools/state.py` — `get_value()`, `set_value()` for state persistence
- `agentic_devtools/cli/git/operations.py` — `branch_has_commits_ahead_of_main()` for ref resolution pattern
- `agentic_devtools/cli/git/core.py` — `run_git()`, `STATE_COMMIT_MESSAGE`, `get_commit_message()`
- `agentic_devtools/cli/azure_devops/commands.py` — existing `create_pull_request()`
- `agentic_devtools/cli/subprocess_utils.py` — `run_safe()` for subprocess calls

**Architecture Decisions:**

- Shared template interpolation module (`agentic_devtools/cli/pr_template.py`) consumed by both platform-specific PR creation commands
- New state key `git.last_commit_message` (output) separate from `commit_message` (input)
- Template at `.agdt/config/pull-request-template.md` — version-controlled, user-owned after creation
- No auto-creation of template during PR creation — explicit `agdt-init-pr-template` command required

## 2. Research Summary

Key decisions:

| Decision | Choice |
| --- | --- |
| Template interpolation engine | Simple `str.replace()` (not Jinja2) — single variable, no conditionals needed |
| Module location | New `agentic_devtools/cli/pr_template.py` — shared utility |
| Git log ref resolution | Mirror `branch_has_commits_ahead_of_main()` pattern: `origin/main` → `main` → fallback |
| Commit separator | Markdown horizontal rule (`---`) between multiple commits |
| GitHub PR creation | New module `agentic_devtools/cli/github/pr_create.py` implemented in Phase 5 so `resolve_pr_body()` is consumed by both PR platforms |

## 3. Design Overview

```text
┌─────────────────────┐     ┌──────────────────────────┐
│ agdt-git-save-work  │────▶│ Persist effective message │
│ (commands.py)       │     │ → git.last_commit_message │
└─────────────────────┘     └──────────────────────────┘

┌─────────────────────────┐     ┌─────────────────────────┐
│ agdt-create-pull-request│────▶│ pr_template.py          │
│ (azure_devops/commands) │     │  resolve_pr_body()      │
│ (github/pr_create)      │     │  ├─ load template       │
└─────────────────────────┘     │  ├─ resolve_full_commit_message()│
                                │  │   ├─ state            │
                                │  │   ├─ git log          │
                                │  │   └─ literal fallback │
                                │  └─ interpolate          │
                                └─────────────────────────┘

┌─────────────────────────┐     ┌─────────────────────────┐
│ agdt-init-pr-template   │────▶│ Create default template  │
│ (pr_template.py)        │     │ at .agdt/config/         │
└─────────────────────────┘     │ pull-request-template.md │
                                └─────────────────────────┘
```

**Data Flow:**

1. `agdt-git-save-work` commits → reads back effective message → persists to `git.last_commit_message`
2. `agdt-create-pull-request` calls `resolve_pr_body()` which:
   - Loads template from `.agdt/config/pull-request-template.md`
   - Resolves `fullCommitMessage` via fallback chain
   - Replaces `{{fullCommitMessage}}` in template
   - Returns final body string
3. Platform-specific command uses returned body in API call

## 4. Implementation Phases

### Phase 1: Shared Template Module (`pr_template.py`)

**Deliverables:**

- New file `agentic_devtools/cli/pr_template.py`
- Functions: `resolve_full_commit_message()`, `resolve_pr_body()`, `init_pr_template()`
- Default template content as a module constant

**Tasks:**

1. **Create `agentic_devtools/cli/pr_template.py`** with:
   - `DEFAULT_TEMPLATE_CONTENT: str` — the German-language operational checklist with `{{fullCommitMessage}}`
   - `TEMPLATE_RELATIVE_PATH = ".agdt/config/pull-request-template.md"`
   - `STATE_KEY_LAST_COMMIT_MESSAGE = "git.last_commit_message"`

2. **Implement `resolve_main_ref() -> str | None`**:
   - Try `git rev-parse --verify origin/main` via `run_git(..., check=False)` → return `"origin/main"`
   - Try `git rev-parse --verify main` via `run_git(..., check=False)` → return `"main"`
   - Return `None` if neither exists
   - Reuse `run_git()` from `cli/git/core.py` and branch on `returncode` (mirror `branch_has_commits_ahead_of_main()`)

3. **Implement `resolve_full_commit_message() -> str`**:
   - Step 1: Check `get_value("git.last_commit_message")` — return if non-empty
   - Step 2: Call `resolve_main_ref()`, run `git log --format=%B%x1e {ref}..HEAD` via `run_git(..., check=False)`
   - Parse output: split on `\x1e` commit delimiters, trim empty entries, join with `\n\n---\n\n` separator
   - Handle single commit (no separator), empty result (no commits ahead), and non-zero `git log` return codes by falling through to Step 3
   - Step 3: Return literal `"No commit message could be found."`

4. **Implement `get_template_path(git_root: Path | None = None) -> Path`**:
   - Resolve git root via existing helper or `run_git("rev-parse", "--show-toplevel")`
   - Return `git_root / ".agdt" / "config" / "pull-request-template.md"`

5. **Implement `resolve_pr_body() -> str`**:
   - Load template file; if missing → warn to stderr, return `resolve_full_commit_message()`
   - If template is empty/whitespace → return `resolve_full_commit_message()`
   - Replace `{{fullCommitMessage}}` with resolved message (simple `str.replace`)
   - Return final content

6. **Implement `init_pr_template() -> None`** (CLI entry point):
   - Get template path
   - If file exists → print "Template already exists at {path}" and return
   - Create parent dirs (`mkdir(parents=True, exist_ok=True)`)
   - Write `DEFAULT_TEMPLATE_CONTENT`
   - Print confirmation

**Tests (TDD — write first):**

- `tests/unit/cli/pr_template/test_resolve_main_ref.py`
- `tests/unit/cli/pr_template/test_resolve_full_commit_message.py`
- `tests/unit/cli/pr_template/test_get_template_path.py`
- `tests/unit/cli/pr_template/test_resolve_pr_body.py`
- `tests/unit/cli/pr_template/test_init_pr_template.py`

---

### Phase 2: Persist Effective Commit Message in `agdt-git-save-work`

**Deliverables:**

- Modified `agentic_devtools/cli/git/commands.py` — persist `git.last_commit_message` after commit/amend
- New state key `git.last_commit_message` populated after every successful commit

**Tasks:**

1. **Add helper `_persist_effective_commit_message(dry_run: bool) -> None`** in `commands.py`:
   - If `dry_run` → skip
   - Run `git log -1 --format=%B` to read back effective message
   - Strip trailing whitespace
   - Call `set_value("git.last_commit_message", message)`

2. **Call the helper after commit/amend** in `save_work()`:
   - After line 257 (new commit) or line 254 (amend) — insert call after the commit step completes
   - Place it before the sync/push steps so it's captured even if push fails

3. **Add constant** `STATE_LAST_COMMIT_MESSAGE = "git.last_commit_message"` in `core.py`

**Tests (TDD):**

- `tests/unit/cli/git/commands/test_persist_effective_commit_message.py`
- Update existing `save_work` tests to verify state key is written

---

### Phase 3: Integrate Template into Azure DevOps PR Creation

**Deliverables:**

- Modified `agentic_devtools/cli/azure_devops/commands.py` — use `resolve_pr_body()` for description

**Tasks:**

1. **Modify `create_pull_request()`** (line 379):
   - Replace `description = get_value("description") or ""` with:

     ```python
     from ..pr_template import resolve_pr_body
     description = resolve_pr_body()
     ```

   - This enforces FR-003/FR-006/FR-007: template rendering is always used when template exists

2. **Update dry-run output** to show resolved body (truncated if long)

**Tests (TDD):**

- `tests/unit/cli/azure_devops/commands/test_create_pull_request.py` — add cases for template resolution

---

### Phase 4: Register CLI Entry Points

**Deliverables:**

- `agdt-init-pr-template` command registered in `pyproject.toml`

**Tasks:**

1. **Add entry point** in `pyproject.toml`:

   ```toml
   agdt-init-pr-template = "agentic_devtools.cli.runner:run_as_script"
   ```

2. **Register command** in `agentic_devtools/cli/runner.py:COMMAND_MAP` (required for `run_as_script` dispatch)

3. **Add `__init__.py`** exports as needed

---

### Phase 5: GitHub PR Creation Integration

**Deliverables:**

- New `agentic_devtools/cli/github/pr_create.py` command module using `gh pr create`
- `agdt-gh-create-pull-request` entry point and runner registration
- GitHub PR creation path uses `resolve_pr_body()` just like Azure DevOps

**Tasks:**

1. **Create `agentic_devtools/cli/github/pr_create.py`**:
   - Implement GitHub PR creation via `gh pr create`
   - Resolve the PR body with `resolve_pr_body()`
   - Pass the resolved content through the GitHub CLI `--body` path
2. **Register the command**:
   - Add `agdt-gh-create-pull-request = "agentic_devtools.cli.runner:run_as_script"` in `pyproject.toml`
   - Add the command to `agentic_devtools/cli/runner.py:COMMAND_MAP`
3. **Share platform behavior**:
   - Reuse the same fallback behavior for missing or empty templates (warning only when the template is missing)
   - Verify `resolve_pr_body()` output is accepted by both Azure `--description` and GitHub `--body`
4. **Add tests (TDD)**:
   - `tests/unit/cli/github/test_pr_create.py` — cover resolved template body, missing-template fallback, and `gh` invocation arguments

---

### Phase 6: Default Template Content

**Deliverables:**

- Finalized default template constant matching the spec's German-language operational checklist

**Template content:**

```markdown
## Checkliste

### Getestet
- [ ] Unit Tests aktualisiert/erstellt
- [ ] Integrationstests aktualisiert/erstellt
- [ ] Manuelle Tests durchgeführt

### Database Schema Changes
- [ ] Migration erstellt
- [ ] Rollback getestet
- [ ] Keine Breaking Changes

### Mgm-CLI Updates
- [ ] CLI-Befehle aktualisiert
- [ ] Hilfetext aktualisiert

### Workbench Infrastruktur Updates
- [ ] Konfiguration aktualisiert
- [ ] Deployment-Skripte angepasst

### Infrastruktur Kommunikation
- [ ] Relevante Teams informiert
- [ ] Dokumentation in Confluence aktualisiert

### Dokumentation
- [ ] README aktualisiert
- [ ] API-Dokumentation aktualisiert
- [ ] Changelog-Eintrag hinzugefügt

## Zusatzinformationen

{{fullCommitMessage}}
```

## 5. Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
| --- | --- | --- | --- |
| `git log` fails on shallow clones (CI) | Medium | Low | Catch errors gracefully, fall through to literal fallback |
| Large commit history causes slow `git log` | Low | Low | `origin/main..HEAD` range limits scope; NFR-002 (<2s) |
| Template file encoding issues (non-ASCII) | Medium | Low | Read/write with `encoding="utf-8"` explicitly |
| Legacy `description` state no longer bypasses template | Medium | Medium | Always render from template; degrade only when template missing/empty |
| `run_git` not importable from `pr_template.py` | Low | Low | Import from `cli.git.core` — already a public API |
| Azure DevOps `--description` length limits | Medium | Low | Document limit; templates are typically <5KB |

## 6. Dependencies

**Internal:**

- `agentic_devtools/cli/git/core.py` — `run_git()` for subprocess git calls
- `agentic_devtools/state.py` — `get_value()`, `set_value()` for state persistence
- `agentic_devtools/cli/subprocess_utils.py` — `run_safe()` (if needed beyond `run_git`)
- `agentic_devtools/cli/azure_devops/commands.py` — modification target for integration

**External:**

- `git` CLI — required for log/rev-parse operations
- `az` CLI — existing Azure DevOps PR creation dependency
- `gh` CLI — required for GitHub PR creation in Phase 5

**No new Python package dependencies required.**

---
*Generated by Copilot SDK (claude-opus-4.6)*
