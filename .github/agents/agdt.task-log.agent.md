---
description: "Task Log: Display task output log"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Display the output log of a background task.

## Prerequisites

- **Required state**: `background.task_id`
- **Set state** (if not already set):

  ```bash
  agdt-set background.task_id <value>
  ```

## Actions

1. Run the command:

   ```bash
   agdt-task-log
   ```

## Expected Outcome

Task output log is printed to stdout.

## Next Step

Command is complete.
