---
description: "Work on Jira Issue - Initiate: Start working on a Jira issue (step 1 of 11)"
handoffs:
  - label: "Continue to Setup"
    agent: "agdt.work-on-jira-issue.setup"
    prompt: "Set up the worktree and branch."
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

Start the work-on-jira-issue workflow and ensure the Jira issue key is set.

## Prerequisites

- **Required state**: `jira.issue_key`
- **Set state** (if not already set):

  ```bash
  agdt-set jira.issue_key <value>
  ```

## Actions

1. Initiate the workflow:

   ```bash
   agdt-initiate-work-on-jira-issue-workflow
   ```

## Expected Outcome

The workflow starts and advances to setup or retrieve based on preflight checks.

## Next Step

Continue to setup or retrieve depending on the preflight outcome.
