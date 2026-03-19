---
description: "Advance Workflow: Advance to next workflow step"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Advance the active workflow to the next step.

## Prerequisites

An active workflow must already be running (for example, `work-on-jira-issue` or `pull-request-review`).
Start a workflow first using a relevant initiate command, such as:
- `agdt-initiate-work-on-jira-issue-workflow`
- `agdt-initiate-pull-request-review-workflow`

## Actions

1. Run the command:

   ```bash
   agdt-advance-workflow [step-name]
   ```

## Expected Outcome

The workflow advances to the specified or next step.

## Next Step

Command is complete.
