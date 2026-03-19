---
description: "Check User Exists: Check if a Jira user exists"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Check if a specific Jira user account exists.

## Prerequisites

- **Required state**: `jira.username`
- **Set state** (if not already set):

  ```bash
  agdt-set jira.username <value>
  ```

## Actions

1. Run the command:

   ```bash
   agdt-check-user-exists
   ```

## Expected Outcome

User existence is confirmed or denied (background task).

## Next Step

Command is complete.
