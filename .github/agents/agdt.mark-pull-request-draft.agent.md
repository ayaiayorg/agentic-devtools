---
description: "Mark PR Draft: Mark a pull request as draft"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Mark a pull request as a draft in Azure DevOps.

## Prerequisites

- **Required state**: `pull_request_id`
- **Set state** (if not already set):

  ```bash
  agdt-set pull_request_id <value>
  ```

## Actions

1. Run the command:

   ```bash
   agdt-mark-pull-request-draft
   ```

## Expected Outcome

The pull request is marked as a draft (background task).

## Next Step

Command is complete.
