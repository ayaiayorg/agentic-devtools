---
description: "PR Review - Initiate: Start a pull request review (step 1 of 5)"
handoffs:
  - label: "Continue to File Review"
    agent: "agdt.pull-request-review.file-review"
    prompt: "Review individual files."

---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Start the pull-request-review workflow and load PR context.

## Prerequisites

- **Required state**: `pull_request_id`, `jira.issue_key`
- **Set state** (if not already set):

  ```bash
  agdt-set pull_request_id <value>
  agdt-set jira.issue_key <value>
  ```

## Actions

1. Start the PR review:

   ```bash
   agdt-review-pull-request
   ```

## Expected Outcome

The review workflow starts and prepares the file review queue.

## Next Step

Continue to file review.
