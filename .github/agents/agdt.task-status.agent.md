---
description: "Task Status: Show detailed task status"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Show detailed status of a specific background task.

## Prerequisites

- **Required state**: `background.task_id`
- **Set state** (if not already set):

  ```bash
  agdt-set background.task_id <value>
  ```

## Actions

1. Run the command:

   ```bash
   agdt-task-status
   ```

## Expected Outcome

Detailed task status is displayed.

## Next Step

Command is complete.
