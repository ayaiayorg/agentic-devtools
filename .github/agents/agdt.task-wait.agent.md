---
description: "Task Wait: Wait for task completion"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Wait for a background task to complete.

## Prerequisites

- **Required state**: `background.task_id`
- **Set state** (if not already set):

  ```bash
  agdt-set background.task_id <value>
  ```

## Actions

1. Run the command:

   ```bash
   agdt-task-wait
   ```

## Expected Outcome

Blocks until the task completes and shows the result.

## Next Step

Command is complete.
