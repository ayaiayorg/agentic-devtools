---
description: "Approve File: Approve a file during PR review"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Approve a file during a pull request review in Azure DevOps.

## Prerequisites

- **Required state**: `pull_request_id`
- **Required state**: `file_review.file_path`
- **Required state**: `file_review.summary`
- **Set state** (if not already set):

  ```bash
  agdt-set pull_request_id <value>
  agdt-set file_review.file_path <value>
  agdt-set file_review.summary <value>
  ```

## Actions

1. Run the command:

   ```bash
   agdt-approve-file
   ```

## Expected Outcome

The file is approved and review state is updated (background task).

## Next Step

Command is complete.
