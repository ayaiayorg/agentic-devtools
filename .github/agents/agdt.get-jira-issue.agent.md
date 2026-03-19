---
description: "Get Jira Issue: Retrieve Jira issue details"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Retrieve full details for a Jira issue, including parent and epic if applicable.

## Prerequisites

- **Required state**: `jira.issue_key`
- **Set state** (if not already set):

  ```bash
  agdt-set jira.issue_key <value>
  ```

## Actions

1. Run the command:

   ```bash
   agdt-get-jira-issue
   ```

## Expected Outcome

Issue details are retrieved and saved to output files (background task).

## Next Step

Command is complete.
