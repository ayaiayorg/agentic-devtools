---
description: "Create PR: Create a new pull request"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Create a new pull request in Azure DevOps.

## Prerequisites

- **Required state**: `source_branch`
- **Required state**: `title`
- **Set state** (if not already set):

  ```bash
  agdt-set source_branch <value>
  agdt-set title <value>
  ```

## Actions

1. Run the command:

   ```bash
   agdt-create-pull-request
   ```

## Expected Outcome

A new pull request is created (background task).

## Next Step

Command is complete.
