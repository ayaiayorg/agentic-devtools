---
description: "Create Epic: Create a new Jira epic"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Create a new epic in Jira.

## Prerequisites

- **Required state**: `jira.summary`
- **Required state**: `jira.epic_name`
- **Required state**: `jira.role`
- **Required state**: `jira.desired_outcome`
- **Required state**: `jira.benefit`
- **Optional state**: `jira.project_key` (defaults if omitted)
- **Set state** (if not already set):

  ```bash
  # Optional project key (uses default if not set)
  agdt-set jira.project_key <value>
  agdt-set jira.summary <value>
  agdt-set jira.epic_name <value>
  agdt-set jira.role <value>
  agdt-set jira.desired_outcome <value>
  agdt-set jira.benefit <value>
  ```

## Actions

1. Run the command:

   ```bash
   agdt-create-epic
   ```

## Expected Outcome

A new Jira epic is created (background task).

## Next Step

Command is complete.
