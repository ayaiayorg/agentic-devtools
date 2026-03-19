---
description: "Confirm Suggestion: Confirm a review suggestion was addressed"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Confirm that a review suggestion has been addressed by the PR author.

## Prerequisites

- **Required state**: `pull_request_id`
- **Set state** (if not already set):

  ```bash
  agdt-set pull_request_id <value>
  ```

## Actions

1. Run the command:

   ```bash
   agdt-confirm-suggestion-addressed
   ```

## Expected Outcome

The suggestion is marked as addressed (background task).

## Next Step

Command is complete.
