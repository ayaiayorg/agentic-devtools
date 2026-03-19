---
description: "Add Users to Role Batch: Batch add users to a role"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Batch add multiple users to a Jira project role.

## Prerequisites

- **Required state**: `jira.project_key`
- **Required state**: `jira.role_id`
- **Required state**: `jira.usernames`
- **Set state** (if not already set):

  ```bash
  agdt-set jira.project_key <value>
  agdt-set jira.role_id <value>
  agdt-set jira.usernames <value>
  ```

## Actions

1. Run the command:

   ```bash
   agdt-add-users-to-project-role-batch
   ```

## Expected Outcome

Users are batch-added to the role (background task).

## Next Step

Command is complete.
