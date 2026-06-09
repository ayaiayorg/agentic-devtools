# Implementation Plan: Jinja2 Commit Message Template System

## 1. Technical Context

| Aspect | Detail |
|--------|--------|
| Language | Python 3.10+ |
| Package | `agentic-devtools` (pip-installable CLI) |
| Template Engine | Jinja2 ≥3.0.0 (already a dependency) |
| State System | JSON state at `.agdt/workflows/{identity}/{worktree_key}/state.json` |
| Config Path | `.agdt/config/commit-template.j2` (repo-root-relative, versionable) |
| Test Framework | pytest with 100% branch coverage requirement |
| Test Structure | 1:1:1 policy under `tests/unit/` |
| CI | ruff lint/format, mypy, coverage, test-structure validator |

### Key Existing Infrastructure

- **Jinja2 environment** with `SilentUndefined` already exists in `prompts/loader.py`
- **State resolution** via `get_value("dotted.key")` with dot-notation nesting
- **`resolve_github_repo()`** in `cli/github/repo_resolution.py` — calls `sys.exit(1)` on failure
- **`_resolve_repo_from_git_remote()`** and `_validate_repo_format()` — non-exiting internal helpers
- **`agdt-setup`** has a `--skip-templates` gate in Platform & Workflow Setup, while `skip_repo_steps` separately gates whether `_run_file_modifying_steps()` runs at all
- **`commit_cmd()`** in `cli/git/commands.py` resolves message at lines 228–231

## 2. Research Summary

Detailed decisions cover:

- Reusing vs. creating a new Jinja2 environment
- Non-exiting repo resolution strategy
- `issueType` mapping implementation
- File-based `commitMessageBody` path resolution

Key decisions:

1. Create a **new dedicated module** `agentic_devtools/cli/git/commit_template.py` (not reuse `prompts/loader.py` directly) to keep concerns separated
2. Reuse `SilentUndefined` class via import from `prompts/loader.py`
3. Implement `resolve_github_repo_safe()` using `_resolve_repo_from_git_remote()` and `_validate_repo_format()` so template rendering uses non-exiting repo resolution without catching `SystemExit`
4. Place `issueType` mapping in a constant dict within the template module

## 3. Design Overview

```text
┌─────────────────────────────────────────────────────────────────┐
│                     agdt-git-save-work                           │
│  (cli/git/commands.py :: commit_cmd)                            │
├─────────────────────────────────────────────────────────────────┤
│  Priority Chain:                                                │
│  1. --commit-message CLI arg  →  use verbatim                   │
│  2. Template rendering        →  resolve_commit_message_from_template() │
│  3. commit_message state key  →  get_commit_message() fallback  │
└────────────────────────┬────────────────────────────────────────┘
                         │ (step 2)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│            cli/git/commit_template.py                            │
├─────────────────────────────────────────────────────────────────┤
│  resolve_commit_message_from_template(git_root: Path | None) -> str|None│
│  ├── _load_template(git_root)                                   │
│  ├── _build_render_context(git_root)                            │
│  │   ├── _resolve_issue_key()                                   │
│  │   ├── _resolve_issue_link(normalized_key, raw_key, git_root) │
│  │   ├── _resolve_issue_type()                                  │
│  │   ├── _resolve_commit_title()                                │
│  │   └── _resolve_commit_body(git_root)                         │
│  ├── _render_template(template_str, context)                    │
│  └── _warn_unresolved_variables(context, template_content)      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│            cli/setup/commit_template_setup.py                    │
├─────────────────────────────────────────────────────────────────┤
│  ensure_commit_template(git_root: Path) -> bool                 │
│  validate_commit_template(git_root: Path) -> list[str]          │
└─────────────────────────────────────────────────────────────────┘
```

## 4. Implementation Phases

### Phase 1: Template Rendering Core (P1 — FR-003, FR-004, FR-005, FR-007)

**Deliverable**: New module `agentic_devtools/cli/git/commit_template.py` that renders commit messages from a Jinja2 template.

#### Tasks

1. **Create `cli/git/commit_template.py`** with:
   - `TEMPLATE_PATH = ".agdt/config/commit-template.j2"` constant
   - `REQUIRED_VARIABLES` set: `{"issueType", "issueKey", "issueLink", "commitMessageTitle", "commitMessageBody"}`
   - `DEFAULT_JIRA_TYPE_MAPPING` dict for issue type → conventional commit type, plus FR-003 configuration override support so defaults are used unless explicitly overridden
   - `resolve_commit_message_from_template(git_root: Path | None) -> str | None`
     - When `git_root` is `None`, the function discovers the git root via
       `run_git(..., check=False)` from `cli/git/core.py`
       (`git rev-parse --show-toplevel`); if discovery returns a non-zero exit
       code (not in a git repo), returns `None` immediately and the caller
       falls through to `get_commit_message()`
     - When `git_root` is provided (e.g., from `commit_cmd()`), it is used directly;
       sub-functions `_load_template()`, `_resolve_commit_body()`, and
       `_resolve_issue_link()` always receive a resolved, non-`None` `Path`
     - Returns `None` when no template exists (caller falls back)
     - Returns rendered string on success
     - Emits warnings and returns `None` on template errors (FR-007)
   - `_load_template(git_root: Path) -> str | None` — reads file, validates non-empty
   - `_build_render_context(git_root: Path) -> dict[str, str]` — resolves all 5 variables; include only resolved values and omit unresolved keys so Jinja2 `SilentUndefined` renders empty strings
   - `_resolve_issue_key() -> tuple[str | None, Any]` — returns `(normalized, raw)` per FR-003 rules
   - `_resolve_issue_link(normalized_key: str | None, raw_key: Any, git_root: Path) -> str | None`
   - `_resolve_issue_type() -> str | None`
   - `_resolve_commit_title() -> str | None`
   - `_resolve_commit_body(git_root: Path) -> str | None`
   - `_warn_unresolved_variables(context: dict[str, str], template_content: str) -> None`
     — parse template via Jinja2 AST/meta to find referenced variables (including filters like
     `{{ issueKey | upper }}`) and warn when referenced variables are missing from context

2. **Create non-exiting repo resolution helper** in `cli/github/repo_resolution.py`:
   - `resolve_github_repo_safe() -> str | None` — same logic as `resolve_github_repo()` but returns `None` instead of calling `sys.exit(1)`

3. **Integrate into `commit_cmd()`** in `cli/git/commands.py`:
   - After CLI arg check, before `get_commit_message()`, call `resolve_commit_message_from_template()`
   - If it returns a string, use it; if `None`, fall through to `get_commit_message()`

4. **Update error message** in `get_commit_message()` to mention template system as alternative

#### Test Files (1:1:1 structure)

```text
tests/unit/cli/git/commit_template/
├── __init__.py
├── test_resolve_commit_message_from_template.py
├── test__load_template.py
├── test__build_render_context.py
├── test__resolve_issue_key.py
├── test__resolve_issue_link.py
├── test__resolve_issue_type.py
├── test__resolve_commit_title.py
├── test__resolve_commit_body.py
└── test__warn_unresolved_variables.py

tests/unit/cli/github/repo_resolution/
├── __init__.py
└── test_resolve_github_repo_safe.py
```

---

### Phase 2: Setup Integration (P1 — FR-001, FR-002, FR-006, FR-008)

**Deliverable**: `agdt-setup` creates and validates the commit template.

#### Tasks

1. **Create `cli/setup/commit_template_setup.py`** with:
   - `DEFAULT_TEMPLATE` constant (the template content from FR-001)
   - `ensure_commit_template(git_root: Path) -> bool` — creates template if missing, returns whether created
   - `validate_commit_template(git_root: Path) -> list[str]` — parse with Jinja2 AST/meta and return required variables not referenced in template

2. **Integrate into `_run_file_modifying_steps()`** in `cli/setup/commands.py`:
   - In the existing "Platform & Workflow Setup" area, alongside the current `if not args.skip_templates:` gate
   - Call `ensure_commit_template(git_root)` to create if needed
   - Call `validate_commit_template(git_root)` to check existing templates
   - Print warnings for missing required variables

3. **Update `--skip-templates` help text** to mention commit template

#### Test Files

```text
tests/unit/cli/setup/commit_template_setup/
├── __init__.py
├── test_ensure_commit_template.py
└── test_validate_commit_template.py
```

---

### Phase 3: Documentation (P2 — FR-009)

**Deliverable**: Updated documentation.

#### Tasks

1. **Update `docs/state-keys.md`**:
   - Add `versionControl.commitMessageType` key
   - Add `versionControl.commitMessageTitle` key
   - Add `versionControl.commitMessageBodyFile` key
   - Add `issueManagement.issueLink` key (optional)
   - Add `issueManagement.issueKey` key (future alias)

2. **Update `.github/copilot-instructions.md`**:
   - Add commit template section describing the feature
   - Document priority chain
   - Document variable resolution

3. **Update `--skip-templates` CLI help text** in `cli/setup/commands.py`

---

### Phase 4: Edge Cases & Hardening (P2 — FR-007 edge cases)

**Deliverable**: Robust handling of all edge cases.

#### Tasks

1. **Empty template handling**: Zero-byte and whitespace-only files → warning + fallback
2. **Syntax error handling**: Catch `jinja2.TemplateSyntaxError` → warning + fallback
3. **Missing `commit_message` fallback**: When template fails AND `commit_message` is empty → actionable error
4. **File read errors for body file**: Permission errors, encoding issues → treat as unresolved
5. **Path traversal safety**: Validate body file path stays within repo

#### Additional Test Coverage

```text
tests/unit/cli/git/commit_template/
└── test_resolve_commit_message_from_template_fallback.py
```

- Extend `test__load_template.py` with the Phase 4 empty-template and syntax-error
  scenarios instead of creating a separate `test__load_template_edge_cases.py` file.

## 5. Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Breaking existing `agdt-git-save-work` flows | High | Low | Template is purely additive; no-template path unchanged; gated by file existence |
| `SilentUndefined` produces unexpected output | Medium | Low | Explicit warning for each unresolved var; empty-string semantics match spec |
| `resolve_github_repo_safe()` logic drift from original | Medium | Medium | Extract shared logic; test both functions against same scenarios |
| Jinja2 `TemplateSyntaxError` in user templates | Low | Medium | Graceful fallback with diagnostic warning (FR-007) |
| Body file path resolution security (path traversal) | Medium | Low | Validate resolved path is within git repo root |
| Performance regression from template I/O | Low | Low | Single file read + Jinja2 render is well under 100ms (NFR-001) |

## 6. Dependencies

### Internal Dependencies

| Module | Dependency Type | Purpose |
|--------|----------------|---------|
| `agentic_devtools/state.py` | Import | `get_value()` for state resolution |
| `agentic_devtools/prompts/loader.py` | Import | Reuse `SilentUndefined` class |
| `agentic_devtools/cli/github/repo_resolution.py` | Import | Non-exiting repo resolution helpers |
| `agentic_devtools/cli/git/core.py` | Import | `run_git()` for git root detection |
| `agentic_devtools/cli/setup/commands.py` | Integration | Setup flow insertion point |

### External Dependencies

| Package | Version | Status |
|---------|---------|--------|
| Jinja2 | ≥3.0.0 | Already declared in `pyproject.toml` |

### Ordering Constraints

- Phase 1 must complete before Phase 2 (setup validates what the renderer uses)
- Phase 1 and Phase 3 can proceed in parallel
- Phase 4 can proceed after Phase 1

---
*Generated by Copilot SDK (claude-opus-4.6)*
