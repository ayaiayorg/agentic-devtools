---
description: "Add PR Comment: Post a comment on a pull request"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Add a new comment to a pull request in Azure DevOps.

## Prerequisites

- **Required state**: `pull_request_id`
- **Required state**: `content`
- **Set state** (if not already set):

  ```bash
  agdt-set pull_request_id <value>
  agdt-set content <value>
  ```

## Actions

1. Run the command:

   ```bash
   agdt-add-pull-request-comment
   ```

## Expected Outcome

A comment is posted to the pull request (background task).

## Next Step

Command is complete.
