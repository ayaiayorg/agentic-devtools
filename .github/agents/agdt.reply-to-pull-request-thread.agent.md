---
description: "Reply to PR Thread: Reply to a comment thread"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Reply to a pull request comment thread in Azure DevOps.

## Prerequisites

- **Required state**: `pull_request_id`
- **Required state**: `thread_id`
- **Required state**: `content`
- **Set state** (if not already set):

  ```bash
  agdt-set pull_request_id <value>
  agdt-set thread_id <value>
  agdt-set content <value>
  ```

## Actions

1. Run the command:

   ```bash
   agdt-reply-to-pull-request-thread
   ```

## Expected Outcome

A reply is posted to the specified thread (background task).

## Next Step

Command is complete.
