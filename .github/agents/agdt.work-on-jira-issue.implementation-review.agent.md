---
description: "Work on Jira Issue - Implementation Review: Review completed checklist (step 7 of 11)"
handoffs:
  - label: "Continue to Verification"
    agent: "agdt.work-on-jira-issue.verification"
    prompt: "Run tests and quality gates."

---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Review the completed checklist items before verification.

## Prerequisites

- **Required state**: `jira.issue_key`
- **Set state** (if not already set):

  ```bash
  agdt-set jira.issue_key <value>
  ```

## Actions

1. Advance the workflow:

   ```bash
   agdt-advance-workflow
   ```

## Expected Outcome

The workflow advances to verification.

## Next Step

Continue to verification.
