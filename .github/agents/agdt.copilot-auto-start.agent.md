---
description: "Copilot Auto-Start: Auto-start a Copilot session"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Auto-start a Copilot CLI session for the current workflow.

## PROHIBITED ACTIONS

**You MUST NEVER invoke any workflow initiation commands or agents**, including but not limited to:

- `@agdt.pull-request-review.initiate`
- `@agdt.work-on-jira-issue.initiate`
- `agdt-initiate-pull-request-review-workflow`
- `agdt-initiate-work-on-jira-issue-workflow`
- Any other `agdt-initiate-*` command

If no active workflow is found after auto-start, report the error and STOP. Do NOT attempt to start a new workflow.

## Prerequisites

An active workflow SHOULD already be running. If the workflow state is not yet available (e.g., due to a race condition with the setup process), the auto-start command will handle waiting internally.

## Actions

1. Run the command:

   ```bash
   agdt-copilot-auto-start
   ```

2. If the command fails or reports no active workflow, output a diagnostic message and STOP. Do NOT fall back to initiating a new workflow.

## Expected Outcome

A Copilot session is started for the already-active workflow.

## Next Step

Command is complete.
