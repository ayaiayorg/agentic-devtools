---
description: "Submit File Review: Submit batched file review"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Submit a batched file review for a pull request.

## Prerequisites

- **Required state**: `pull_request_id`
- **Set state** (if not already set):

  ```bash
  agdt-set pull_request_id <value>
  ```

## Actions

1. Run the command:

   ```bash
   agdt-submit-file-review
   ```

## Expected Outcome

The batched file review is submitted (background task).

## Next Step

Command is complete.
