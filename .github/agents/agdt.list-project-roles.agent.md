---
description: "List Project Roles: List Jira project roles"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

List all roles for a Jira project.

## Prerequisites

- **Required state**: `jira.project_key`
- **Set state** (if not already set):

  ```bash
  agdt-set jira.project_key <value>
  ```

## Actions

1. Run the command:

   ```bash
   agdt-list-project-roles
   ```

## Expected Outcome

Project roles are listed (background task).

## Next Step

Command is complete.
