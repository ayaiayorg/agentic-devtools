---
description: "Break Down Issue - Initiate: Break down a Jira issue into subtasks"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Start the break-down-issue-into-subtasks workflow to decompose a Jira issue into actionable subtasks.

## Prerequisites

- **Issue context (required)**: one of the following must be provided:
  - Pass `--issue-key <KEY>` to `agdt-initiate-break-down-issue-into-subtasks-workflow`, or
  - Ensure `jira.issue_key` is already set in state (for example: `agdt-set jira.issue_key PROJECT-1234`)
- **Optional CLI arguments**:
  - `--user-request "<TEXT>"` to pass the user's natural-language request or constraints into the workflow
  - `--interactive true` to run the workflow in interactive mode; default is non-interactive/headless (`false`)

## Actions

1. Run the workflow initiation command using one of the following options:

   **Option A — Explicit issue key via CLI argument (recommended for clarity):**

   ```bash
  agdt-initiate-break-down-issue-into-subtasks-workflow --issue-key <KEY> [--user-request "<TEXT>"] [--interactive true]
   ```

   **Option B — Use `jira.issue_key` from state (no `--issue-key` flag):**

   ```bash
   # Assumes jira.issue_key is already set in state (e.g. via: agdt-set jira.issue_key PROJECT-1234)
   agdt-initiate-break-down-issue-into-subtasks-workflow
   ```

## Expected Outcome

The workflow starts and the issue is ready for subtask decomposition.

## Next Step

Command is complete.
