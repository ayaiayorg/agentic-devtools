---
description: "Advance Workflow: Advance to next workflow step"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Advance an **already-active** workflow to the next step. This agent does NOT start workflows — it only advances existing ones.

## PROHIBITED ACTIONS

**You MUST NEVER invoke any of the following commands or agents**, regardless of the circumstances:

- `@agdt.pull-request-review.initiate`
- `@agdt.work-on-jira-issue.initiate`
- `agdt-initiate-pull-request-review-workflow`
- `agdt-initiate-work-on-jira-issue-workflow`
- `agdt-initiate-apply-pr-suggestions-workflow`
- `agdt-initiate-create-jira-epic-workflow`
- `agdt-initiate-create-jira-issue-workflow`
- `agdt-initiate-create-jira-subtask-workflow`
- `agdt-initiate-update-jira-issue-workflow`
- `agdt-initiate-optimize-issue-for-ai-agent-workflow`
- `agdt-initiate-break-down-issue-into-subtasks-workflow`
- `agdt-initiate-pr-merge-orchestrator-workflow`

This prohibition applies even when no active workflow is found. If a workflow is not active, you **STOP** and report the error — you do not attempt to fix the situation by starting a new workflow.

## Prerequisites

An active workflow MUST already be running. If no workflow is active, this agent reports a diagnostic error and stops.

## Actions

1. Check workflow state:

   ```bash
   agdt-get-workflow
   ```

2. If the output shows an **active** workflow, advance it:

   ```bash
   agdt-advance-workflow [step-name]
   ```

3. If the output shows **no active workflow** or a completed/cleared workflow:
   a. Output: "No active workflow detected. Retrying in 4 seconds..."
   b. Wait 4 seconds using:

      ```bash
      python3 -c "import time; time.sleep(4)"
      ```

      If `python3` is not available, try `python -c "import time; time.sleep(4)"`, then `py -c "import time; time.sleep(4)"`.

   c. Retry once:

      ```bash
      agdt-get-workflow
      ```

   d. If now active, run `agdt-advance-workflow [step-name]`
   e. If still not active, output the failure diagnostics below and **STOP**

## Failure Output Format

When no active workflow is found after the retry, output the following diagnostic message **exactly**:

```text
No active workflow found.

State directory checked: <full absolute path from agdt-get-workflow output or from running: python3 -c "from agentic_devtools.state import get_state_dir; print(get_state_dir().resolve())">
Requested step: <step-name or "next (auto)">

No re-initiation will be attempted. This agent only advances existing workflows.

Troubleshooting:
- Run: agdt-get-workflow (to inspect current workflow state)
- Run: agdt-show (to inspect all state values)
- If the workflow was started from a different directory, the state directory may not match (see issue #1913).
```

Do NOT modify any state. Do NOT invoke any other agent. STOP here.

## Expected Outcome

The workflow advances to the specified or next step, OR a clear diagnostic error is displayed.

## Next Step

Command is complete.
