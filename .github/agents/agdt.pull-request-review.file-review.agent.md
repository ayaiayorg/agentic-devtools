---
description: "PR Review - File Review: Review individual files (step 2 of 5)"
handoffs:
  - label: "Continue File Review"
    agent: "agdt.pull-request-review.file-review"
    prompt: "Review the next file."
  - label: "Continue to Summary"
    agent: "agdt.pull-request-review.summary"
    prompt: "Generate the review summary."

---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Review files and record approvals or requested changes.

## Prerequisites

- **Required state**: `pull_request_id`, `file_review.file_path`
- **Set state** (if not already set):

  ```bash
  agdt-set pull_request_id <value>
  agdt-set file_review.file_path <value>
  ```

## Actions

1. Approve the file:

   ```bash
   agdt-approve-file
   ```

2. Request changes:

   ```bash
   agdt-request-changes
   ```

## Expected Outcome

File review feedback is recorded and the queue advances.

## Next Step

Continue file review or move to summary.
