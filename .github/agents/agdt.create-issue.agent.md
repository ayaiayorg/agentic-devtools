---
description: "Create Issue: Create a new Jira issue"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Create a new issue in Jira.

## Prerequisites

- **Required state**: `jira.summary`
- **Required state**: `jira.role`
- **Required state**: `jira.desired_outcome`
- **Required state**: `jira.benefit`
- **Optional state** (defaults may apply): `jira.project_key`
- **Set state** (if not already set):

  ```bash
  # Optional: omit to use the default Jira project
  agdt-set jira.project_key <value>
  agdt-set jira.summary <value>
  agdt-set jira.role "<user role>"
  agdt-set jira.desired_outcome "<desired outcome>"
  agdt-set jira.benefit "<business benefit>"
  ```

## Actions

1. Run the command:

   ```bash
   agdt-create-issue
   ```

## Expected Outcome

A new Jira issue is created (background task).

## Next Step

Command is complete.
