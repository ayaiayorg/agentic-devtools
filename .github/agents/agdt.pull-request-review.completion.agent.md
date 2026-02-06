---
description: "PR Review - Completion: Finalize review (step 5 of 5)"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Finalize the review and add any Jira follow-up comment.

## Prerequisites

- **Required state**: `pull_request_id`
- **Set state** (if not already set):

  ```bash
  agdt-set pull_request_id <value>
  ```

## Actions

1. Post a Jira follow-up comment:

   ```bash
   agdt-add-jira-comment
   ```

## Expected Outcome

The PR review workflow is completed.

## Next Step

Workflow is complete.
