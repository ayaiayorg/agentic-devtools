---
description: "Work on Jira Issue - Retrieve: Fetch Jira issue details (step 3 of 11)"
handoffs:
  - label: "Continue to Planning"
    agent: "agdt.work-on-jira-issue.planning"
    prompt: "Analyze the issue and draft a plan."

---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Fetch Jira issue details and populate state for planning.

## Prerequisites

- **Required state**: `jira.issue_key`
- **Set state** (if not already set):

  ```bash
  agdt-set jira.issue_key <value>
  ```

## Actions

1. Fetch the Jira issue:

   ```bash
   agdt-get-jira-issue
   ```

## Expected Outcome

Jira issue details are stored in state and the workflow is ready for planning.

## Next Step

Continue to the planning step.
