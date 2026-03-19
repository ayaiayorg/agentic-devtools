---
description: "Find Role ID: Find a Jira role ID by name"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Find a Jira project role ID by its name.

## Prerequisites

- **Required state**: `jira.project_key`
- **Required state**: `jira.role_name`
- **Set state** (if not already set):

  ```bash
  agdt-set jira.project_key <value>
  agdt-set jira.role_name <value>
  ```

## Actions

1. Run the command:

   ```bash
   agdt-find-role-id-by-name
   ```

## Expected Outcome

The role ID is returned (background task).

## Next Step

Command is complete.
