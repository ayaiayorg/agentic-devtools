---
description: "Reject Suggestion: Reject a suggestion resolution"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Reject a suggestion resolution during re-review.

## Prerequisites

- **Required state**: `pull_request_id`
- **Set state** (if not already set):

  ```bash
  agdt-set pull_request_id <value>
  ```

## Actions

1. Run the command:

   ```bash
   agdt-reject-suggestion-resolution
   ```

## Expected Outcome

The suggestion resolution is rejected (background task).

## Next Step

Command is complete.
