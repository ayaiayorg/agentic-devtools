---
description: "Request Changes with Suggestion: Request changes with code suggestions"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Request changes on a file with structured code replacement suggestions.

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
   agdt-request-changes-with-suggestion
   ```

## Expected Outcome

Changes with code suggestions are requested (background task).

## Next Step

Command is complete.
