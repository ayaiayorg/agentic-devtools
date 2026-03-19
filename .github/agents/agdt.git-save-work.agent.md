---
description: "Git Save Work: Stage, commit/amend, and push changes"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Stage all changes, create a new commit or amend the existing one, and push to origin.

## Prerequisites

- **Required state**: `commit_message`
- **Set state** (if not already set):

  ```bash
  agdt-set commit_message <value>
  ```

## Actions

1. Run the command:

   ```bash
   agdt-git-save-work
   ```

## Expected Outcome

Changes are committed and pushed (background task).

## Next Step

Command is complete.
