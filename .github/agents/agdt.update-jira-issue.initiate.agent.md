---
description: "Update Jira Issue - Initiate: Update an existing Jira issue"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Start the update-jira-issue workflow and prepare the update payload.

## Prerequisites

- **Required state**: `jira.issue_key`
- **Set state** (if not already set):

  ```bash
  agdt-set jira.issue_key <value>
  ```

## Actions

1. Initiate issue update:

   ```bash
   agdt-initiate-update-jira-issue-workflow
   ```

## Expected Outcome

The workflow starts and is ready for update inputs.

## Next Step

Workflow is complete.
