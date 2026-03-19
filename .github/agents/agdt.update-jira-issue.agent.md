---
description: "Update Jira Issue: Update Jira issue fields"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Update fields on an existing Jira issue.

## Prerequisites

- **Required state**: `jira.issue_key`
- **Required update input**: at least one of:
  - `jira.summary`
  - `jira.description`
  - `jira.labels`
  - `jira.labels_add`
  - `jira.labels_remove`
  - `jira.assignee`
  - `jira.priority`
  - `jira.custom_fields`
- **Set state** (example):

  ```bash
  agdt-set jira.issue_key DFLY-1234
  agdt-set jira.summary "Updated summary"
  ```

## Actions

1. Verify `jira.issue_key` is set and at least one update field is provided.
2. Run the command:

   ```bash
   agdt-update-jira-issue
   ```

## Expected Outcome

A background task starts to update the Jira issue. If no update fields are provided, the command exits with an error.

## Next Step

Command is complete.
