---
description: "Create Subtask: Create a new Jira subtask"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Create a new subtask in Jira under a parent issue.

## Prerequisites

- **Required state**: `jira.parent_key`
- **Required state**: `jira.summary`
- **Required state**: `jira.role`
- **Required state**: `jira.desired_outcome`
- **Required state**: `jira.benefit`
- **Set state** (if not already set):

  ```bash
  agdt-set jira.parent_key <value>
  agdt-set jira.summary <value>
  agdt-set jira.role <value>
  agdt-set jira.desired_outcome <value>
  agdt-set jira.benefit <value>
  ```

## Actions

1. Run the command:

   ```bash
   agdt-create-subtask
   ```

## Expected Outcome

A new Jira subtask is created (background task).

## Next Step

Command is complete.
