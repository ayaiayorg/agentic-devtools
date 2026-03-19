---
description: "Resolve Thread: Resolve a PR comment thread"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Resolve a pull request comment thread in Azure DevOps.

## Prerequisites

- **Required state**: `pull_request_id`
- **Required state**: `thread_id`
- **Set state** (if not already set):

  ```bash
  agdt-set pull_request_id <value>
  agdt-set thread_id <value>
  ```

## Actions

1. Run the command:

   ```bash
   agdt-resolve-thread
   ```

## Expected Outcome

The specified thread is resolved (background task).

## Next Step

Command is complete.
