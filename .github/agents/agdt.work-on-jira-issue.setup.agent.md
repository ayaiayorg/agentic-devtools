---
description: "Work on Jira Issue - Setup: Create worktree and branch (step 2 of 11)"
handoffs:
  - label: "Continue to Retrieve"
    agent: "agdt.work-on-jira-issue.retrieve"
    prompt: "Fetch Jira issue details."

---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Create the worktree and branch for the Jira issue when preflight checks fail.

## Prerequisites

- **Required state**: `jira.issue_key`
- **Set state** (if not already set):

  ```bash
  agdt-set jira.issue_key <value>
  ```

## Actions

1. Run the automated setup:

   ```bash
   agdt-setup-worktree-background
   ```

## Expected Outcome

A new worktree and branch are created, and VS Code opens in the correct context.

## Next Step

Proceed to retrieve the Jira issue details.
