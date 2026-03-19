---
description: "Get PR Threads: Retrieve all comment threads"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Retrieve all comment threads on a pull request.

## Prerequisites

- **Required state**: `pull_request_id`
- **Set state** (if not already set):

  ```bash
  agdt-set pull_request_id <value>
  ```

## Actions

1. Run the command:

   ```bash
   agdt-get-pull-request-threads
   ```

## Expected Outcome

PR threads are retrieved and saved to an output file (background task).

## Next Step

Command is complete.
