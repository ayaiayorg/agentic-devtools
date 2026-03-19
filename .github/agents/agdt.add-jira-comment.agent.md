---
description: "Add Jira Comment: Add a comment to a Jira issue"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Add a comment to a Jira issue.

## Prerequisites

- **Required state**: `jira.issue_key`
- **Required state**: `jira.comment`
- **Set state** (if not already set):

  ```bash
  agdt-set jira.issue_key <value>
  agdt-set jira.comment <value>
  ```

## Actions

1. Run the command:

   ```bash
   agdt-add-jira-comment
   ```

## Expected Outcome

A comment is added to the Jira issue (background task).

## Next Step

Command is complete.
