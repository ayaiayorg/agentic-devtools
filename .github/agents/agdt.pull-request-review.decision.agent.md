---
description: "PR Review - Decision: Approve or request changes (step 4 of 5)"
handoffs:
  - label: "Continue to Completion"
    agent: "agdt.pull-request-review.completion"
    prompt: "Finalize the review."

---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Decide whether to approve or request changes for the pull request.

## Prerequisites

- **Required state**: `pull_request_id`
- **Set state** (if not already set):

  ```bash
  agdt-set pull_request_id <value>
  ```

## Actions

1. Approve the pull request:

   ```bash
   agdt-approve-pull-request
   ```

2. Request changes with a comment:

   ```bash
   agdt-add-pull-request-comment
   ```

## Expected Outcome

The review decision is recorded and the workflow moves to completion.

## Next Step

Continue to completion.
