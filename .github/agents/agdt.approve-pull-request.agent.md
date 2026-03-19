---
description: "Approve PR: Approve a pull request with sentinel banner"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Approve a pull request with an approval sentinel banner in Azure DevOps.

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
   agdt-approve-pull-request
   ```

## Expected Outcome

The pull request is approved with a sentinel banner (background task).

## Next Step

Command is complete.
