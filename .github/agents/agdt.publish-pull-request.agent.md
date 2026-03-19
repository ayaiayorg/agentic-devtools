---
description: "Publish PR: Publish a draft pull request"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Publish a draft pull request in Azure DevOps.

## Prerequisites

- **Required state**: `pull_request_id`
- **Set state** (if not already set):

  ```bash
  agdt-set pull_request_id <value>
  ```

## Actions

1. Run the command:

   ```bash
   agdt-publish-pull-request
   ```

## Expected Outcome

The draft pull request is published (background task).

## Next Step

Command is complete.
