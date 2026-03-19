---
description: "Get PR Details: Retrieve full pull request details"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Retrieve full pull request details including diff, threads, and iterations.

## Prerequisites

- **Required state**: `pull_request_id`
- **Set state** (if not already set):

  ```bash
  agdt-set pull_request_id <value>
  ```

## Actions

1. Run the command:

   ```bash
   agdt-get-pull-request-details
   ```

## Expected Outcome

Full PR details are saved to an output file (background task).

## Next Step

Command is complete.
