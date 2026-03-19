---
description: "Get Role Details: Get Jira project role details"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Get details of a specific Jira project role.

## Prerequisites

- **Required state**: `jira.project_key`
- **Required state**: `jira.role_id`
- **Set state** (if not already set):

  ```bash
  agdt-set jira.project_key <value>
  agdt-set jira.role_id <value>
  ```

## Actions

1. Run the command:

   ```bash
   agdt-get-project-role-details
   ```

## Expected Outcome

Role details are returned (background task).

## Next Step

Command is complete.
