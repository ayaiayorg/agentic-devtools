---
name: workflow-analysis
description: "Reusable domain knowledge for analyzing agentic-devtools workflows: bug taxonomy, analysis methodology, structured output schema, and prioritization framework."
version: "1.0.0"
---

# Workflow Analysis Skill

Shared domain knowledge for analyzing `agentic-devtools` workflows and producing
structured bug/optimization reports. Downstream agents consume this skill by reading
it directly from the package source tree.

**Consumers:**

- `agdt.analyze-workflow` — uses the taxonomy and methodology sections
- `agdt.create-issues-from-analysis` — uses the JSON schema to parse analysis output
- `agdt.workflow-audit` — orchestrates all sections end-to-end

---

## Bug Taxonomy & Severity Classification

### Bug Categories

Every finding must be classified into exactly one of the 8 categories below.
The **Category Slug** (kebab-case) is the value used in the JSON schema `category` field.

| Category Slug | Display Name | Definition | Example |
|---|---|---|---|
| `race-condition` | Race Condition | Temporal ordering bug between async operations where one side reads state before the other side has written it. | `agdt_run_id` not yet written to state when auto-start injection reads it (`worktree_setup.py`). |
| `cascading-failure` | Cascading Failure | Bug A prevents Bug B's mitigation from working, creating a chain of failures. | Missing `pending-auto-start.json` marker prevents terminal `sendSequence` fallback from activating (`worktree_setup.py`). |
| `silent-failure` | Silent Failure | Operation fails but logs or reports success, hiding the real problem. | Background task log claims auto-start succeeded when no `tasks.json` was written (`worktree_setup.py`). |
| `missing-integration` | Missing Integration | Code path that should call a function but doesn't, leaving a gap in the workflow. | `clear_state_for_workflow_initiation()` not preserving `agdt_run_id` across nested invocations (`commands.py`). |
| `configuration-gap` | Configuration Gap | Required setting not injected or validated before the code path that depends on it. | `task.allowAutomaticTasks` VS Code setting not set in `.vscode/settings.json` (`worktree_setup.py`). |
| `timeout-inadequacy` | Timeout Inadequacy | Default timeouts insufficient for real-world conditions, causing premature termination. | `auto_execute_timeout` reduced to 60 s but PR review setup takes 120 s+ (`worktree_setup.py`). |
| `state-lifecycle-bug` | State Lifecycle Bug | State written or cleared at the wrong time in the workflow, causing reads to see stale or missing data. | Workflow state cleared by nested `clear_state_for_workflow_initiation()` before parent reads it (`state.py`, `commands.py`). |
| `observability-gap` | Observability Gap | Insufficient logging, misleading messages, or lost output that prevents effective debugging. | "Environment setup complete!" logged before review setup actually finishes (`worktree_setup.py`). |

### Severity Levels

Each finding must be assigned exactly one severity level. The **Weight** column
provides the integer value used in the prioritization scoring formula.

| Level | Weight | Definition | Criteria |
|---|---|---|---|
| `critical` | 10 | Root cause that blocks the entire feature. | Has downstream cascade to other findings; fixing it unblocks multiple issues. |
| `high` | 7 | Directly causes a user-visible failure. | Causes user-visible failure OR cascades from a critical bug. |
| `medium` | 4 | Reduces reliability, correctness, or debuggability. | Does not block the feature but degrades quality or developer experience. |
| `low` | 1 | Nice-to-have improvement. | Workarounds exist; impact is cosmetic or minor. |

---

## Structured Analysis Output Schema

### JSON Schema (draft-07)

The following JSON Schema defines the structure of analysis output produced by
`agdt.analyze-workflow` and consumed by `agdt.create-issues-from-analysis`.

> **Note:** `cascade_graph` keys are string representations of integer finding IDs
> (JSON object keys must be strings). The `cascades_from` and `cascades_to` fields
> use integer IDs. This asymmetry is intentional — JSON requires object keys to be
> strings, but integer IDs are more natural for cross-referencing within the
> `findings` array.

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Workflow Analysis Output",
  "description": "Structured output from an agentic-devtools workflow analysis session.",
  "type": "object",
  "required": [
    "workflow",
    "analyzed_at",
    "entry_point",
    "source_files_analyzed",
    "findings",
    "priority_order",
    "cascade_graph"
  ],
  "properties": {
    "workflow": {
      "type": "string",
      "description": "Kebab-case workflow identifier (e.g. 'pull-request-review-autostart')."
    },
    "analyzed_at": {
      "type": "string",
      "format": "date-time",
      "description": "ISO-8601 UTC timestamp of when the analysis was performed."
    },
    "entry_point": {
      "type": "string",
      "description": "CLI command that starts the workflow (e.g. 'agdt-initiate-pull-request-review-workflow')."
    },
    "source_files_analyzed": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Repo-relative paths of all source files read during analysis."
    },
    "log_files_analyzed": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Absolute paths of log files used as evidence."
    },
    "findings": {
      "type": "array",
      "items": { "$ref": "#/$defs/Finding" },
      "description": "Ordered list of findings."
    },
    "priority_order": {
      "type": "array",
      "items": { "type": "integer" },
      "description": "Finding IDs sorted by descending priority score."
    },
    "cascade_graph": {
      "type": "object",
      "additionalProperties": {
        "type": "array",
        "items": { "type": "integer" }
      },
      "description": "Maps finding ID (as string key) to array of downstream finding IDs it causes."
    }
  },
  "additionalProperties": false,
  "$defs": {
    "Finding": {
      "type": "object",
      "required": [
        "id",
        "title",
        "category",
        "severity",
        "affected_files",
        "affected_functions",
        "description",
        "evidence",
        "suggested_fix",
        "cascades_from",
        "cascades_to",
        "priority_score"
      ],
      "properties": {
        "id": {
          "type": "integer",
          "minimum": 1,
          "description": "Unique sequential identifier (1-based)."
        },
        "title": {
          "type": "string",
          "description": "Short descriptive title."
        },
        "category": {
          "type": "string",
          "enum": [
            "race-condition",
            "cascading-failure",
            "silent-failure",
            "missing-integration",
            "configuration-gap",
            "timeout-inadequacy",
            "state-lifecycle-bug",
            "observability-gap"
          ],
          "description": "One of the 8 taxonomy category slugs."
        },
        "severity": {
          "type": "string",
          "enum": ["critical", "high", "medium", "low"],
          "description": "Severity level from the taxonomy."
        },
        "affected_files": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Repo-relative paths of affected source files."
        },
        "affected_functions": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Function or method names within affected files."
        },
        "description": {
          "type": "string",
          "description": "Detailed description of the finding."
        },
        "evidence": {
          "type": "string",
          "description": "Concrete evidence: log excerpts, code references, or reproduction steps."
        },
        "suggested_fix": {
          "type": "string",
          "description": "Recommended fix approach."
        },
        "cascades_from": {
          "type": ["integer", "null"],
          "description": "ID of the finding this cascades from, or null if it is a root cause."
        },
        "cascades_to": {
          "type": "array",
          "items": { "type": "integer" },
          "description": "IDs of findings caused by this one (empty array if none)."
        },
        "priority_score": {
          "type": "integer",
          "description": "Computed score: severity_weight + cascade_impact + fixability_bonus."
        }
      },
      "additionalProperties": false
    }
  }
}
```

### Annotated Example

The example below shows a single finding from the PR review workflow autostart
analysis (`agdt_run_id` race condition):

```json
{
  "workflow": "pull-request-review-autostart",
  "analyzed_at": "2026-04-07T12:00:00Z",
  "entry_point": "agdt-initiate-pull-request-review-workflow",
  "source_files_analyzed": [
    "agentic_devtools/cli/workflows/worktree_setup.py",
    "agentic_devtools/cli/workflows/commands.py",
    "agentic_devtools/state.py",
    "agentic_devtools/background_tasks.py"
  ],
  "log_files_analyzed": [
    "/home/user/.agdt/workflows/default/pr-review/background-tasks/logs/autostart_20260407.log"
  ],
  "findings": [
    {
      "id": 1,
      "title": "agdt_run_id race condition",
      "category": "race-condition",
      "severity": "critical",
      "affected_files": [
        "agentic_devtools/cli/workflows/worktree_setup.py"
      ],
      "affected_functions": [
        "_maybe_inject_auto_start_before_vscode"
      ],
      "description": "The agdt_run_id is not yet written to state when the auto-start injection reads it. The run ID is generated inside run_function_in_background(), but _maybe_inject_auto_start_before_vscode() reads it synchronously before the background task has a chance to write it.",
      "evidence": "Log shows: 'Auto-start injection skipped: missing agdt_run_id in state'. Timestamp of log entry is 0.3s before the background task writes the run ID.",
      "suggested_fix": "Generate the run ID before spawning the background task and pass it as a parameter. Move the set_value('agdt_run_id', run_id) call to the synchronous parent function.",
      "cascades_from": null,
      "cascades_to": [4, 5],
      "priority_score": 13
    }
  ],
  "priority_order": [1],
  "cascade_graph": {
    "1": [4, 5]
  }
}
```

**Score breakdown for finding #1:**

- `severity_weight` = 10 (critical)
- `cascade_impact` = 2 (cascades to findings #4 and #5)
- `fixability_bonus` = +1 (fix is ~15 lines of code)
- **`priority_score` = 10 + 2 + 1 = 13**

---

## Analysis Methodology

Follow these 8 steps sequentially when analyzing any `agentic-devtools` workflow.
Each step builds on the output of previous steps.

1. **Entry point identification** — Locate the CLI command that starts the workflow
   and trace it to its handler function. CLI entry points are defined in `pyproject.toml`
   under `[project.scripts]`. Handler functions live in `agentic_devtools/cli/` and its
   subpackages. Record the command name, the Python module path, and the handler function
   name.

2. **Call graph traversal** — Follow the handler through all function calls, paying
   special attention to cross-module boundaries. Track calls into
   `background_tasks.py` → `run_function_in_background()` for background task spawning,
   and `run_safe()` in `agentic_devtools/cli/git/core.py` for subprocess execution.
   Document every function call with its source file, line number, and whether it is
   synchronous or asynchronous.

3. **State lifecycle mapping** — For every `get_value()`, `set_value()`, and
   `clear_workflow_state()` call in `agentic_devtools/state.py` (and callers), record the
   state key, the operation (read, write, or delete), and the call site (file + function).
   Build a timeline showing when each key is written and when it is first read. Flag any
   read-before-write patterns.

4. **Async boundary identification** — Identify every point where the workflow crosses
   an async boundary: calls to `run_function_in_background()` in `background_tasks.py`,
   `subprocess.Popen` / `run_safe()` invocations in `agentic_devtools/cli/git/core.py`,
   and `Popen` calls in `agentic_devtools/cli/workflows/worktree_setup.py`. For each
   boundary, document the parent→child data contract: what data the parent passes, what
   the child is expected to produce, and where the result is stored.

5. **Failure mode enumeration** — For each async boundary identified in step 4,
   enumerate three failure scenarios: (a) the child process has not completed yet when
   the parent reads the result, (b) the child process fails silently (exits 0 but
   produces no output), and (c) the child process exceeds its timeout. For each scenario,
   describe the observable symptom and the state of the system afterward.

6. **Log evidence collection** — Read log files from
   `.agdt/workflows/{identity}/{worktree_key}/background-tasks/logs/` to find actual
   error messages, timestamps, and state snapshots. Compare log timestamps against the
   state lifecycle timeline from step 3 to confirm or refute hypothesized failure modes
   from step 5. Quote specific log lines as evidence.

7. **Cascade analysis** — Build a directed graph where nodes are findings and edges
   point from cause to effect. Finding X cascades to finding Y if fixing X would
   eliminate or mitigate Y. Record the graph in the `cascade_graph` field of the output
   schema. Identify root causes (nodes with no incoming edges) and terminal effects
   (nodes with no outgoing edges).

8. **Prioritization** — Compute the `priority_score` for each finding using the
   formula defined in the Prioritization Framework section. Sort findings by descending
   score and record the order in the `priority_order` field. Root causes with high
   cascade impact should naturally bubble to the top.

---

## Prioritization Framework

### Scoring Formula

```text
priority_score = severity_weight + cascade_impact + fixability_bonus
```

| Component | Definition | Values |
|---|---|---|
| `severity_weight` | Integer weight from the severity level table. | critical=10, high=7, medium=4, low=1 |
| `cascade_impact` | Count of findings in the **transitive closure** of `cascades_to`. | 0, 1, 2, ... |
| `fixability_bonus` | Adjustment based on estimated fix complexity. | +1 if < 20 lines, 0 if 20–100 lines, -1 if > 100 lines or architectural |

### Worked Examples

**Finding 1: `agdt_run_id` race condition**

- severity = critical → `severity_weight` = 10
- `cascades_to` = [4, 5] → `cascade_impact` = 2
- Fix is ~15 lines → `fixability_bonus` = +1
- **`priority_score` = 10 + 2 + 1 = 13**

**Finding 4: `pending-auto-start.json` never written**

- severity = high → `severity_weight` = 7
- `cascades_to` = [] → `cascade_impact` = 0
- Fix is ~8 lines → `fixability_bonus` = +1
- **`priority_score` = 7 + 0 + 1 = 8**

**Finding 9: misleading success log message**

- severity = medium → `severity_weight` = 4
- `cascades_to` = [] → `cascade_impact` = 0
- Fix is ~3 lines → `fixability_bonus` = +1
- **`priority_score` = 4 + 0 + 1 = 5**

### Interpretation

Higher scores indicate findings that should be fixed first. Root causes with
cascade impact naturally score higher, ensuring the fix order minimizes wasted
effort. When two findings have the same score, prefer the one with higher cascade
impact (it unblocks more downstream fixes).

---

## Markdown Report Template

Use this template to produce the human-readable companion report alongside the
JSON output. Replace `{placeholder}` values with analysis data.

<!-- markdownlint-disable MD024 -->

````markdown
# Workflow Analysis: `{workflow_name}`

**Date:** {analyzed_at}
**Entry Point:** `{entry_point}`
**Symptom:** {symptom_description}

---

## Executive Summary

{executive_summary}

---

## Findings

{for each finding, ordered by priority_score descending:}

### {id}. {title} ({severity} — {category})

**Priority Score:** {priority_score}

#### What happened

{description}

#### Evidence

{evidence}

#### Impact

{impact_description}
{if cascades_to: "Cascades to: " + linked finding titles}

#### Affected Code

{for each affected_files + affected_functions}
- `{file}` — `{function}()`

#### Suggested Fix

{suggested_fix}

---

## Cascade Graph

{ASCII or mermaid diagram of the cascade_graph}

## Priority Order

| Priority | ID | Title | Severity | Score |
|---|---|---|---|---|
{for each finding in priority_order}
| {rank} | {id} | {title} | {severity} | {priority_score} |

## Files Analyzed

{bullet list of source_files_analyzed}
````

<!-- markdownlint-enable MD024 -->
