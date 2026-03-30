---
description: "PR Review - File Review: Review individual files (step 2 of 4)"
handoffs:
  - label: "Continue File Review"
    agent: "agdt.pull-request-review.file-review"
    prompt: "Review the next file."
  - label: "Continue to Decision"
    agent: "agdt.pull-request-review.decision"
    prompt: "Approve or request changes."

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

1. Hand off to `@agdt.approve-file` to approve a single file.
2. Hand off to `@agdt.request-changes` to request changes on a single file.
3. Use `agdt-approve-files` to batch-approve multiple files with a shared summary.
4. Use `agdt-submit-reviews` to batch-submit reviews with defaults and per-item overrides.
5. Use `agdt-request-changes-batch` to batch request-changes for multiple files.

## Expected Outcome

File review feedback is recorded and the queue advances.

## Next Step

Continue file review or move to decision.
