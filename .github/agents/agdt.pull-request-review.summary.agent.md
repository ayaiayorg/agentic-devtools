---
description: "PR Review - Summary: Generate review summary (step 3 of 5)"
handoffs:
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

Generate the pull request review summary.

## Prerequisites

- **Required state**: `pull_request_id`
- **Set state** (if not already set):

  ```bash
  agdt-set pull_request_id <value>
  ```

## Actions

1. Generate the summary:

   ```bash
   agdt-generate-pr-summary
   ```

## Expected Outcome

A review summary is generated and ready for a decision.

## Next Step

Continue to decision.
