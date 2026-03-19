---
description: "Request Changes: Request changes on a file"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Request changes on a file during a pull request review.

## Prerequisites

- **Required state**: `pull_request_id`
- **Required state**: `file_review.file_path`
- **Required state**: `file_review.summary`
- **Required state**: `file_review.suggestions`
- **Set state** (if not already set):

  ```bash
  agdt-set pull_request_id <value>
  agdt-set file_review.file_path <value>
  agdt-set file_review.summary <value>
  agdt-set file_review.suggestions <value>
  ```

## Actions

1. Run the command:

   ```bash
   agdt-request-changes
   ```

## Expected Outcome

Changes are requested and review state is updated (background task).

## Next Step

Command is complete.
