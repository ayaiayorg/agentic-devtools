---
description: "Mark File Reviewed: Mark a file as reviewed"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Mark a file as reviewed in Azure DevOps (visible as 'viewed' icon in PR UI).

## Prerequisites

- **Required state**: `pull_request_id`
- **Required state**: `file_review.file_path`
- **Set state** (if not already set):

  ```bash
  agdt-set pull_request_id <value>
  agdt-set file_review.file_path <value>
  ```

## Actions

1. Run the command:

   ```bash
   agdt-mark-file-reviewed
   ```

## Expected Outcome

The file is marked as reviewed (background task).

## Next Step

Command is complete.
