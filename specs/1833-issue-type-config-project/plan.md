# Implementation Plan: Issue Type Config in project.json

**Issue**: [#1833](https://github.com/ayaiayorg/agentic-devtools/issues/1833)

## 1. Technical Context

| Aspect | Detail |
|--------|--------|
| Language | Python 3.10+ |
| Package | `agentic_devtools` (pip-installable CLI) |
| Config file | `.agdt/config/project.json` — per-repo, team-shareable JSON |
| Config module | `agentic_devtools/cli/config/project_config.py` — `load_project_config()`, `save_project_config()` |
| State system | `agentic_devtools/state.py` — dot-notation `get_value("versionControl.commitMessageType")` |
| Setup flow | `agentic_devtools/cli/setup/commands.py` → `_prompt_project_config()` |
| Git commit path | `agentic_devtools/cli/git/commands.py` → `commit_cmd()` |
| Test framework | pytest with 1:1:1 test structure under `tests/unit/` |
| Coverage | 100% branch coverage per source file (enforced in CI) |
| Lint/Format | ruff check + ruff format |

### Key Dependencies

- `agentic_devtools/cli/config/project_config.py` — `load_project_config()` for reading config
- `agentic_devtools/state.py` — `get_value()` for reading `versionControl.commitMessageType` from state
- `specs/1829-jinja2-commit-message-template/spec.md` — defines the template system that will consume the resolved issue type

## 2. Research Summary

See [research.md](research.md) for detailed decisions. Key choices:

1. **New module**: `agentic_devtools/cli/config/commit_type_resolution.py` (per clarification)
2. **Deterministic helpers**: Resolution/validation return values and warning strings; callers may emit warnings to stderr
3. **camelCase canonical**: Fields stored as `defaultCommitIssueType` / `availableCommitIssueTypes`; snake_case aliases accepted on read only
4. **Non-blocking validation**: Warnings returned to callers (who may emit to stderr); operations never blocked

## 3. Design Overview

### Resolution Flow

```text
resolve_commit_issue_type(explicit_type, project_config)
  │
  ├─ 1. explicit_type (from state/CLI versionControl.commitMessageType)
  │     → if non-empty string, use it
  │
  ├─ 2. project_config["defaultCommitIssueType"]
  │     (fallback: project_config["default_commit_issue_type"])
  │     → if valid non-empty string, use it
  │
  └─ 3. Hardcoded fallback: "feat"
```

### Validation Flow

```text
validate_commit_issue_type(resolved_type, allowed_types)
  │
  ├─ allowed_types empty/absent → use STANDARD_COMMIT_TYPES
  ├─ resolved_type in allowed → return None (no warning)
  └─ resolved_type NOT in allowed → return warning string
```

### Module Architecture

```text
agentic_devtools/cli/config/
├── __init__.py                    # Updated: re-export new public symbols
├── project_config.py              # Unchanged
└── commit_type_resolution.py      # NEW: all resolution + validation logic
```

### Public API (new module)

```python
# Constants
STANDARD_COMMIT_TYPES: list[str]

# Core functions
def resolve_commit_issue_type(
    explicit_type: str | None = None,
    *,
    project_config: dict[str, Any] | None = None,
) -> tuple[str, list[str]]:
    """Return (resolved_type, warnings) — warnings are complete strings."""

def validate_commit_issue_type(
    issue_type: str,
    allowed_types: list[str],
) -> str | None:
    """Return a warning string or None."""

# Config reading helpers
def read_default_commit_type(
    project_config: dict[str, Any],
) -> tuple[str | None, str | None]:
    """Return (value, warning_or_none) from config with alias support."""

def read_available_commit_types(
    project_config: dict[str, Any],
) -> tuple[list[str], str | None]:
    """Return (types_list, warning_or_none) from config with alias support."""
```

## 4. Implementation Phases

### Phase 1: Core Resolution Module (TDD)

**Deliverable**: `agentic_devtools/cli/config/commit_type_resolution.py` with full test coverage.

#### Step 1.1 — Constants and Type Helpers

Create the new module with:

- `STANDARD_COMMIT_TYPES` constant: `["feat", "fix", "docs", "style", "refactor", "perf", "test", "build", "ci", "chore", "revert"]`
- `_MAX_DISPLAYED_TYPES = 20` — truncation threshold
- `_escape_single_quote(value: str) -> str` — escapes `\` then `'` for warning messages

**Tests** (write first per TDD):

- `tests/unit/cli/config/commit_type_resolution/test_standard_commit_types.py`
- `tests/unit/cli/config/commit_type_resolution/test__escape_single_quote.py`

#### Step 1.2 — Config Reading Helpers

Implement `read_default_commit_type()` and `read_available_commit_types()`:

- **`read_default_commit_type(project_config)`**: Check `defaultCommitIssueType` first, then
  `default_commit_issue_type`. Return `(value, warning)` where `warning` is a warning message
  string when the config value is a non-string type, or `None` otherwise.
  Caller prints warning if needed. Empty string → `(None, None)`.
- **`read_available_commit_types(project_config)`**: Check
  `availableCommitIssueTypes` first, then `available_commit_issue_types`.
  Return `(list, warning)`. Empty array → standard types. Non-array or array
  with non-string elements → standard types + warning.

**Tests** (write first):

- `tests/unit/cli/config/commit_type_resolution/test_read_default_commit_type.py`
- `tests/unit/cli/config/commit_type_resolution/test_read_available_commit_types.py`

#### Step 1.3 — Validation Function

Implement `validate_commit_issue_type(issue_type, allowed_types)`:

- Case-sensitive comparison
- Returns `None` when valid
- Returns `"Warning: Issue type '<type>' is not in availableCommitIssueTypes. Allowed: ['item1', 'item2']"` when invalid
- Truncation: >20 entries → show first 19 + `'and N more'`
- Single-quote escaping per FR-004 spec

**Tests** (write first):

- `tests/unit/cli/config/commit_type_resolution/test_validate_commit_issue_type.py`

#### Step 1.4 — Resolution Function

Implement `resolve_commit_issue_type(explicit_type, *, project_config)`:

- Priority: explicit_type → config default → `"feat"` hardcoded fallback
- When `project_config is None`, calls `load_project_config()` internally (note: loader-level malformed/unreadable-config warnings may still print to `stderr`)
- Reads both config fields via helpers from Step 1.2
- Validates resolved type against allowed types (Step 1.3)
- Detects misconfigured default (FR-005) without duplicate warnings
- Returns `(resolved_type, list_of_warning_strings)`

**Tests** (write first):

- `tests/unit/cli/config/commit_type_resolution/test_resolve_commit_issue_type.py` — must cover all 8+ scenarios from SC-004

#### Step 1.5 — Module Exports

Update `agentic_devtools/cli/config/__init__.py` to re-export:

- `STANDARD_COMMIT_TYPES`
- `resolve_commit_issue_type`
- `validate_commit_issue_type`

### Phase 2: Setup Integration

**Deliverable**: setup defaults are written with per-field idempotency, and explicit commit type overrides are wired into state.

#### Step 2.1 — Update `_prompt_project_config()`

In `agentic_devtools/cli/setup/commands.py`, after the existing config dict is assembled (around line 468–476), add logic to inject defaults for the two new fields:

```python
# Per-field idempotency: write default only if neither camelCase nor snake_case alias exists
if "defaultCommitIssueType" not in config and "default_commit_issue_type" not in config:
    config["defaultCommitIssueType"] = "feat"
if "availableCommitIssueTypes" not in config and "available_commit_issue_types" not in config:
    config["availableCommitIssueTypes"] = list(STANDARD_COMMIT_TYPES)
```

**Tests**: Add or update tests in the setup test directory covering:

- Fresh config gets both fields
- Existing camelCase key preserved
- Existing snake_case alias preserved
- Mixed: one present, one absent → only missing field added

#### Step 2.2 — Wire Explicit Override Source (FR-003)

Ensure the `agdt-git-save-work --commit-message-type <type>` path is explicitly mapped into
state as `versionControl.commitMessageType` so commit type resolution logic can consume it as
the highest-priority input.

**Tests**: Add or update git command tests to cover:

- CLI `--commit-message-type` sets `versionControl.commitMessageType`
- Existing state value path remains backward-compatible for resolution

### Phase 3: Documentation

**Deliverable**: Updated docs in at least 2 locations (SC-005).

#### Step 3.1 — Copilot Instructions

Update the root `.github/copilot-instructions.md` to document:

- New `project.json` fields: `defaultCommitIssueType`, `availableCommitIssueTypes`
- Resolution priority order
- Validation behavior (non-blocking warnings)

#### Step 3.2 — Setup Help Text

Ensure the `agdt-setup` output or help text mentions the commit type configuration fields and their defaults when displaying the project configuration section.

### Phase 4: Verification

#### Step 4.1 — Full Test Suite

```bash
agdt-test
agdt-task-wait
```

#### Step 4.2 — Targeted Checks

```bash
agdt-test-pattern tests/unit/cli/config/commit_type_resolution/
```

#### Step 4.3 — Pre-push Validation

```bash
bash scripts/targeted-checks.sh
```

## 5. Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| `load_project_config()` adds latency to commit path | Medium | Low | Function already optimized for single file read; NFR-001 ≤5ms easily met for simple JSON parse |
| Breaking existing `agdt-setup` behavior | High | Low | Per-field idempotency preserves all existing keys; `dict(existing)` pattern already used |
| camelCase/snake_case confusion in tests | Low | Medium | Constants for both key names; clear docstrings on precedence |
| Spec #1829 template system not yet implemented | None | N/A | This feature is independent — provides resolution logic that #1829 will consume; no circular dependency |

## 6. Dependencies

### Internal Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| `project_config.py` → `load_project_config()` | Exists | Called when `project_config` param is `None` |
| `state.py` → `get_value()` | Exists | Used by callers to read `versionControl.commitMessageType` before calling resolution |
| `cli/setup/commands.py` → `_prompt_project_config()` | Exists | Modified to inject defaults |

### External Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| Spec #1829 (Jinja2 commit template) | In progress | Will consume `resolve_commit_issue_type()` — not a blocker for this feature |

### Test File Manifest

All test files to create (1:1:1 structure):

```text
tests/unit/cli/config/commit_type_resolution/__init__.py
tests/unit/cli/config/commit_type_resolution/test_standard_commit_types.py
tests/unit/cli/config/commit_type_resolution/test__escape_single_quote.py
tests/unit/cli/config/commit_type_resolution/test_read_default_commit_type.py
tests/unit/cli/config/commit_type_resolution/test_read_available_commit_types.py
tests/unit/cli/config/commit_type_resolution/test_validate_commit_issue_type.py
tests/unit/cli/config/commit_type_resolution/test_resolve_commit_issue_type.py
```

---
*Generated by Copilot SDK (claude-opus-4.6)*
