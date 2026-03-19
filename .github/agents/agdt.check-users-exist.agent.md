---
description: "Check Users Exist: Check if multiple Jira users exist"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Check if multiple Jira user accounts exist.

## Prerequisites

- **Required state**: `jira.usernames`
- **Set state** (if not already set):

  ```bash
  agdt-set jira.usernames <value>
  ```

## Actions

1. Run the command:

   ```bash
   agdt-check-users-exist
   ```

## Expected Outcome

User existence results are returned (background task).

## Next Step

Command is complete.
