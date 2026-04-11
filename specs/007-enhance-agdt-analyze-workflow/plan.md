# Implementation Plan: Enhance agdt.analyze-workflow

**Feature:** #1179 — Enhance the `agdt.analyze-workflow` agent with parameterized
invocation, multi-identity log scanning, external worktree context, and a new
`external_context` output field.

**Source Spec:** [`spec.md`](./spec.md)

---

## 1. Technical Context

### Technology Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Language | Python 3.10+ | Matches `requires-python = ">=3.10"` in `pyproject.toml` |
| CLI Framework | argparse | All workflow commands use argparse via `commands.py` |
| Entry Points | `pyproject.toml` `[project.scripts]` → `agentic_devtools.cli.runner:run_as_script` | Standard agdt pattern |
| State | JSON files in `.agdt/workflows/{identity}/{worktree_key}/` | Via `state.py` |
| Agent | `.github/agents/agdt.analyze-workflow.agent.md` | Copilot Chat agent |
| Prompt | `.github/prompts/agdt.analyze-workflow.prompt.md` | 351-line structured prompt |
| Skill | `_bundled_skills/workflow-analysis/SKILL.md` | Bug taxonomy + JSON schema |
| Tests | pytest, 1:1:1 structure under `tests/unit/` | 100% coverage requirement |

### Key Dependencies

- `agentic_devtools/state.py` — `get_state_dir()`, `_sync_bootstrap_for_context_key()`,
  `_resolve_identity()`, `_get_git_repo_root()`, identity/bootstrap resolution
- `agentic_devtools/cli/workflows/commands.py` — Workflow command patterns (argparse,
  `_effective_argv`, `_ensure_scoped_bootstrap_and_clear`)
- `agentic_devtools/cli/runner.py` — `COMMAND_MAP` for CLI dispatch
- `agentic_devtools/_bundled_skills/workflow-analysis/SKILL.md` — JSON schema to extend
- `agentic_devtools/cli/git/agdt_branch.py` — `resolve_worktree_key()` resolution chain

### Architecture Decisions

1. **Agent-driven, not CLI-driven**: The analyze-workflow feature is an AI agent
   that reads code and logs. The enhancement adds Python helper functions that the
   agent calls via `python -c "..."` one-liners, keeping the agent as the
   orchestrator.
2. **No new CLI entry point** (initially): The agent is invoked via Copilot Chat
   (`/agdt.analyze-workflow`), not as a standalone CLI command. A future
   `agdt-analyze-workflow` CLI wrapper can be added later without breaking changes.
3. **Helper module, not a workflow**: The new Python code is a utility module
   (`agentic_devtools/cli/analysis/`), not a formal workflow with state-machine
   steps, because the agent drives the analysis interactively.

---

## 2. Research Summary

| # | Decision | Alternatives Rejected |
|---|----------|-----------------------|
| R1 | New `agentic_devtools/cli/analysis/` package for helper functions | Embedding helpers directly in the prompt (brittle); adding to `state.py` (unrelated concern) |
| R2 | Agent parameters via `$ARGUMENTS` parsing in the prompt, not argparse CLI | Adding a full CLI command (premature — agent is the consumer); using state keys only (less ergonomic) |
| R3 | Extend SKILL.md JSON schema with optional `external_context` field | New separate schema file (fragmentation); breaking change to required fields (backward compat violation) |
| R4 | Multi-identity scanning reads `.agdt/workflows/*/` directories | Single-identity only (misses evidence from other agents); database index (overengineered) |
| R5 | Read-only safety enforced by helper functions returning data, never writing to external paths | OS-level read-only mount (impractical); trust-based approach (unsafe) |

---

## 3. Design Overview

### High-Level Architecture

```text
┌─────────────────────────────────────────────────────────┐
│  Copilot Chat Agent: agdt.analyze-workflow              │
│  (.github/agents/agdt.analyze-workflow.agent.md)        │
│                                                         │
│  $ARGUMENTS: <workflow> [--issue-key K | --pr-id N]     │
│              [--static-only]                            │
├─────────────────────────────────────────────────────────┤
│  Prompt: .github/prompts/agdt.analyze-workflow.prompt.md│
│                                                         │
│  Phase 0 (NEW): Parse parameters, resolve context       │
│  Phase 1: Parse input & load skill (existing)           │
│  Phase 2: Execute 8-step methodology (enhanced Step 6)  │
│  Phase 3: Produce output (enhanced with external_context│
│  Phase 4: Validation (enhanced schema check)            │
└──────┬──────────────────┬──────────────────────┬────────┘
       │                  │                      │
       ▼                  ▼                      ▼
┌──────────────┐  ┌───────────────┐  ┌──────────────────┐
│ SKILL.md     │  │ Python helpers│  │ State directory   │
│ (extended    │  │ (NEW module)  │  │ (output target)   │
│  schema)     │  │               │  │                   │
│              │  │ resolve_      │  │ {state_dir}/      │
│ external_    │  │ analysis_     │  │   workflow-        │
│ context      │  │ context()     │  │   analysis/       │
│ field added  │  │               │  │                   │
│              │  │ scan_identity_│  │                   │
│              │  │ logs()        │  │                   │
│              │  │               │  │                   │
│              │  │ list_identity_│  │                   │
│              │  │ directories() │  │                   │
└──────────────┘  └───────────────┘  └──────────────────┘
```

### Data Flow

```text
Agent receives $ARGUMENTS
  ├─ Parse: workflow_name, --issue-key OR --pr-id, --static-only
  ├─ Mutual exclusion check: --issue-key and --pr-id cannot coexist
  │
  ├─ Resolve worktree context:
  │   ├─ --issue-key K → worktree_key = K
  │   ├─ --pr-id N     → worktree_key = PR{N}
  │   └─ (neither)     → current bootstrap worktree_key
  │
  ├─ Determine analysis scope:
  │   ├─ Source files: always from agent's own repo (cwd)
  │   ├─ Log files: scan ALL identity dirs for matching worktree_key
  │   │   └─ Each log entry prefixed: [identity: {name}]
  │   └─ External worktree (if not --static-only):
  │       └─ Read-only log evidence from external worktree state dirs
  │
  ├─ Execute 8-step methodology (existing, enhanced Step 6)
  │
  └─ Write output to caller's state_dir:
      ├─ {workflow_name}-analysis.json  (includes external_context)
      └─ {workflow_name}-analysis.md
```

### Module Layout (New Code)

```text
agentic_devtools/cli/analysis/
├── __init__.py              # Package exports
├── context_resolver.py      # Resolve worktree context from parameters
├── identity_scanner.py      # Multi-identity log directory scanning
└── external_context.py      # External worktree log collection
```

---

## 4. Implementation Phases

### Phase 1: Python Helper Module (`agentic_devtools/cli/analysis/`)

**Deliverables:** New Python package with three modules providing helper functions
the agent calls via `python -c "..."` one-liners.

#### Task 1.1: Create `context_resolver.py`

**Purpose:** Resolve the analysis target (worktree_key, state directories) from
`--issue-key` or `--pr-id` parameters, matching `state.py`'s resolution precedence.

**Functions:**

- `resolve_analysis_context(issue_key=None, pr_id=None) -> AnalysisContext`
  - Mutual exclusion: raises `ValueError` if both are provided
  - Resolution precedence (matching `_sync_bootstrap_for_context_key()`):
    1. `issue_key` → worktree_key = issue_key (string, stripped)
    2. `pr_id` → worktree_key = `PR{pr_id}` (int → string)
    3. Neither → read current worktree_key from bootstrap
  - Returns `AnalysisContext` dataclass with: `worktree_key`, `source`,
    `git_root`, `caller_state_dir`
  - Caller's state dir is always the agent's current `get_state_dir()`

- `list_worktree_state_dirs(worktree_key) -> list[WorktreeStateDir]`
  - Scans `.agdt/workflows/*/` for directories containing `worktree_key`
  - Returns list of `WorktreeStateDir(identity, path, has_logs)` tuples

**Test files** (1:1:1):

- `tests/unit/cli/analysis/context_resolver/test_resolve_analysis_context.py`
- `tests/unit/cli/analysis/context_resolver/test_list_worktree_state_dirs.py`

#### Task 1.2: Create `identity_scanner.py`

**Purpose:** Scan all identity directories under `.agdt/workflows/` for log
evidence, attributing each with the identity name.

**Functions:**

- `scan_identity_logs(git_root, worktree_key, workflow_name=None) -> list[LogEvidence]`
  - Iterates all directories under `.agdt/workflows/` (skipping `_unscoped`)
  - For each identity dir, looks for `{worktree_key}/background-tasks/logs/`
  - Optionally filters logs matching `workflow_name` in filename
  - Returns `LogEvidence(identity, path, modified_time)` list
  - Read-only: never writes to any scanned directory

- `list_identity_directories(git_root) -> list[IdentityDir]`
  - Lists all identity directories under `.agdt/workflows/` (skipping `_unscoped`,
    consistent with `scan_identity_logs()`)
  - Reads `.identity-owner` files for email attribution
  - Returns `IdentityDir(name, path, owner_email)` list

- `format_evidence_prefix(identity) -> str`
  - Returns `[identity: {identity}]` prefix string

**Test files** (1:1:1):

- `tests/unit/cli/analysis/identity_scanner/test_scan_identity_logs.py`
- `tests/unit/cli/analysis/identity_scanner/test_list_identity_directories.py`
- `tests/unit/cli/analysis/identity_scanner/test_format_evidence_prefix.py`

#### Task 1.3: Create `external_context.py`

**Purpose:** Collect log evidence from external worktrees (other repos sharing the
same `.agdt/` directory) in read-only mode.

**Functions:**

- `collect_external_context(git_root, worktree_key, static_only=False) -> ExternalContext | None`
  - If `static_only` is True, returns `None` (no external worktree scanning)
  - Discovers git worktrees via `git worktree list --porcelain`
  - For each worktree that is not the current one:
    - Reads log files from its state directory (read-only)
    - Collects log evidence with identity attribution
  - Returns `ExternalContext` dataclass when external worktrees are found,
    or `None` when no external worktrees exist (consistent contract:
    `None` means "nothing to report", not an empty container)
  - **Read-only safety:** Only reads files; never writes, creates, or modifies
    anything in external worktree paths

- `build_external_context_field(external_ctx) -> dict | None`
  - Converts `ExternalContext` to the JSON-serializable dict for the output schema
  - Returns `None` when `external_ctx` is `None`; the caller serializes
    this as `"external_context": null` in the JSON output (the field is
    always present — set to `null` when no external context, never omitted)

**Test files** (1:1:1):

- `tests/unit/cli/analysis/external_context/test_collect_external_context.py`
- `tests/unit/cli/analysis/external_context/test_build_external_context_field.py`

#### Task 1.4: Create `__init__.py` with package exports

**Exports:**

```python
from .context_resolver import AnalysisContext, resolve_analysis_context, list_worktree_state_dirs
from .identity_scanner import scan_identity_logs, list_identity_directories, format_evidence_prefix
from .external_context import collect_external_context, build_external_context_field
```

---

### Phase 2: Extend SKILL.md JSON Schema

**Deliverable:** Add optional `external_context` field to the Workflow Analysis
Output JSON Schema.

#### Task 2.1: Add `external_context` to schema

Add to the `properties` of the root object in SKILL.md's JSON Schema:

```json
"external_context": {
  "oneOf": [
    { "$ref": "#/$defs/ExternalContext" },
    { "type": "null" }
  ],
  "description": "Context from external worktrees (null when --static-only or no external worktrees)."
}
```

Add `ExternalContext` to `$defs`:

```json
"ExternalContext": {
  "type": "object",
  "required": ["worktrees_scanned", "log_evidence"],
  "properties": {
    "worktrees_scanned": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Paths of external worktrees that were scanned for log evidence."
    },
    "log_evidence": {
      "type": "array",
      "items": { "$ref": "#/$defs/ExternalLogEvidence" },
      "description": "Log evidence collected from external worktrees."
    },
    "identities_scanned": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Identity directory names that were scanned."
    }
  },
  "additionalProperties": false
}
```

The complete `ExternalContext` and `ExternalLogEvidence` data models are
defined by the `$defs` entries above and the frozen dataclasses in
`external_context.py` (see Task 1.3).

#### Task 2.2: Update annotated example

Add an example showing `external_context: null` (static-only) and a populated
`external_context` to the SKILL.md annotated example section.

**Backward compatibility:** The `external_context` field is optional (not in
`required`). Existing analysis outputs without this field remain valid. The
`create-issues-from-analysis` agent ignores unknown top-level fields.

---

### Phase 3: Update Agent Prompt

**Deliverable:** Enhanced `.github/prompts/agdt.analyze-workflow.prompt.md` with
new Phase 0, enhanced Step 6, and enhanced Phase 3 output.

#### Task 3.1: Add Phase 0 — Parameter Parsing & Context Resolution

Insert new Phase 0 before existing Phase 1:

````markdown
## Phase 0: Parameter Parsing & Context Resolution

### 0.1 Parse Extended Arguments

Extract from `$ARGUMENTS`:
- `{workflow_name}` — required kebab-case workflow identifier (existing)
- `--issue-key {K}` — optional issue key for worktree scoping
- `--pr-id {N}` — optional PR ID for worktree scoping
- `--static-only` — optional flag to disable external worktree scanning

### 0.2 Mutual Exclusion Check

If both `--issue-key` and `--pr-id` are present:
> ERROR: --issue-key and --pr-id are mutually exclusive. Provide one or neither.

### 0.3 Resolve Analysis Context

Run the Python helper to resolve the analysis target:
```bash
python -c "from agentic_devtools.cli.analysis import resolve_analysis_context; ..."
```

### 0.4 Scan Identity Directories

Run the Python helper to discover all identity directories and their logs...
````

#### Task 3.2: Enhance Step 6 — Log Evidence Collection

Update Step 6 to use multi-identity log scanning:

- Replace single-directory log search with call to `scan_identity_logs()`
- Attribute each log excerpt with `[identity: {name}]` prefix
- When `--static-only` is not set, also call `collect_external_context()`
- Merge external log evidence into the findings' `evidence` fields

#### Task 3.3: Enhance Phase 3 — Output with `external_context`

Update Phase 3.2 (Write JSON Output) to include the `external_context` field:

- When external context was collected → populate the field
- When `--static-only` or no external worktrees → set to `null`
- Update the example JSON template to show the field

#### Task 3.4: Enhance Phase 4 — Validation

Add validation check:

> 7\. If `external_context` is present (not null), validate it contains
> `worktrees_scanned` and `log_evidence` fields.

#### Task 3.5: Update Error Handling table

Add new rows:

| Condition | Action |
|-----------|--------|
| Both `--issue-key` and `--pr-id` provided | Print mutual exclusion error and **stop** |
| `--issue-key` or `--pr-id` value missing | Print usage error and **stop** |
| No identity directories found | Proceed with code-only evidence. Note in findings. |
| External worktree inaccessible | Log warning, continue with available evidence |
| `--static-only` with external worktrees present | Respect flag — skip external scanning |

---

### Phase 4: Update Agent Definition

**Deliverable:** Updated `.github/agents/agdt.analyze-workflow.agent.md`.

#### Task 4.1: Update agent description

Update the description to reflect new capabilities:

```markdown
description: "Analyze Workflow: Perform deep code analysis with multi-identity
log scanning, external worktree context, and parameterized scoping via
--issue-key or --pr-id"
```

#### Task 4.2: Update expected input documentation

Update the `## User Input` section to document:

```text
Expected input: a kebab-case workflow name, optionally followed by:
  --issue-key <KEY>  Scope analysis to a specific issue's worktree state
  --pr-id <N>        Scope analysis to a specific PR's worktree state
  --static-only      Disable external worktree log scanning
```

---

### Phase 5: Tests

**Deliverable:** Comprehensive test suite following 1:1:1 structure.

#### Task 5.1: Test `context_resolver.py` functions

| Test file | Covers |
|-----------|--------|
| `test_resolve_analysis_context.py` | Happy path (issue-key), happy path (pr-id), neither (bootstrap fallback), both (mutual exclusion error), empty issue-key, non-integer pr-id |
| `test_list_worktree_state_dirs.py` | Multiple identities found, no matching directories, `_unscoped` skipped, permission errors handled |

#### Task 5.2: Test `identity_scanner.py` functions

| Test file | Covers |
|-----------|--------|
| `test_scan_identity_logs.py` | Logs found across identities, workflow name filter, no logs found, empty identity dirs, `.identity-owner` attribution |
| `test_list_identity_directories.py` | Multiple identities, empty workflows dir, missing `.identity-owner` |
| `test_format_evidence_prefix.py` | Standard format, special characters in identity name |

#### Task 5.3: Test `external_context.py` functions

| Test file | Covers |
|-----------|--------|
| `test_collect_external_context.py` | External worktrees found, static-only returns None, no external worktrees, inaccessible worktree (graceful), read-only safety (no writes) |
| `test_build_external_context_field.py` | Populated context → dict, None context → None |

#### Task 5.4: Run full test suite

```bash
agdt-test
agdt-task-wait
```

Verify all existing tests still pass (backward compatibility NFR).

---

### Phase 6: Integration Validation

**Deliverable:** End-to-end verification that the enhanced agent works correctly.

#### Task 6.1: Verify Python helpers are callable

```bash
python -c "from agentic_devtools.cli.analysis import resolve_analysis_context; print('OK')"
python -c "from agentic_devtools.cli.analysis import scan_identity_logs; print('OK')"
python -c "from agentic_devtools.cli.analysis import collect_external_context; print('OK')"
```

#### Task 6.2: Verify backward compatibility

- Existing analysis output (without `external_context`) still validates
- `create-issues-from-analysis` agent ignores `external_context` field
- No changes to existing `COMMAND_MAP` entries or CLI commands

#### Task 6.3: Run PR checks

```bash
bash scripts/run-pr-checks.sh
```

---

## 5. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Breaking existing analysis JSON schema | Low | High | `external_context` is optional (not in `required`). Existing outputs remain valid. |
| Agent prompt too long for context window | Medium | Medium | Phase 0 is concise (~40 lines). Helper functions offload complexity to Python. |
| Multi-identity scanning performance | Low | Low | Identity directories are typically < 10. File listing is O(n) on directory entries. |
| Read-only safety violation | Low | Critical | Helper functions return data only. No `open(..., 'w')` or `Path.write_*()` calls on external paths. Test coverage enforces this. |
| External worktree resolution failure | Medium | Low | Graceful degradation: inaccessible worktrees logged as warnings, analysis continues with available evidence. |
| Backward compat for `create-issues-from-analysis` | Low | Medium | That agent reads `findings`, `priority_order`, `cascade_graph` — none of which change. `external_context` is a new top-level field it can ignore. |

---

## 6. Dependencies

### Internal Dependencies

| Dependency | Usage | Risk |
|-----------|-------|------|
| `state.py` — `get_state_dir()` | Output directory resolution | Stable API, no changes needed |
| `state.py` — `_resolve_identity()` | Understanding identity derivation | Read-only reference for matching logic |
| `state.py` — `_get_git_repo_root()` | Git root discovery | Stable API, no changes needed |
| `cli/git/agdt_branch.py` — `resolve_worktree_key()` | Resolution precedence reference | Read-only reference; helpers mirror the logic |
| `SKILL.md` — JSON Schema | Schema extension target | Additive change only (new optional field) |
| `cli/runner.py` — `COMMAND_MAP` | No changes needed (agent-driven, not CLI) | None |

### External Dependencies

| Dependency | Usage | Risk |
|-----------|-------|------|
| `git worktree list --porcelain` | External worktree discovery | Requires git ≥ 2.5 (universally available) |
| `.agdt/workflows/` directory structure | Multi-identity scanning | Established convention; documented in `state.py` |
| Copilot Chat agent framework | Agent invocation | Stable; no framework changes needed |

### Out of Scope

- New CLI entry point `agdt-analyze-workflow` (future enhancement)
- Modifying external worktree state files
- Adding new bug taxonomy categories to SKILL.md
- Changing existing JSON schema required fields
- Writing to directories outside the caller's state directory
- Overlay file creation (tracked separately in #1135)

---

*Generated for issue #1179*
