---
description: "PR Review - Decision: Approve or request changes (step 3 of 4)"
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

1. Hand off to `@agdt.approve-pull-request` to approve the pull request.

2. Hand off to `@agdt.add-pull-request-comment` to request changes with a comment.

## Expected Outcome

The review decision is recorded and the workflow moves to completion.

## Next Step

Continue to completion.
