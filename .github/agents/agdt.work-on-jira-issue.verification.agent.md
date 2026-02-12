---
description: "Work on Jira Issue - Verification: Run tests and quality gates (step 8 of 11)"
handoffs:
  - label: "Continue to Commit"
    agent: "agdt.work-on-jira-issue.commit"
    prompt: "Stage and commit changes."

---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Run tests and quality checks before committing.

## Prerequisites

- **Required state**: `jira.issue_key`
- **Set state** (if not already set):

  ```bash
  agdt-set jira.issue_key <value>
  ```

## Actions

1. Run the test suite:

   ```bash
   agdt-test
   ```

2. Advance the workflow:

   ```bash
   agdt-advance-workflow
   ```

## Expected Outcome

Tests pass and the workflow advances to commit.

## Next Step

Continue to commit.
