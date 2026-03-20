---
description: "Work on Jira Issue - Commit: Stage and commit changes (step 9 of 11)"
handoffs:
  - label: "Continue to Pull Request"
    agent: "agdt.work-on-jira-issue.pull-request"
    prompt: "Create a pull request."

---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Stage and commit the changes for the Jira issue.

## Prerequisites

- **Required state**: `commit_message`
- **Set state** (if not already set):

  ```bash
  agdt-set commit_message <value>
  ```

## Actions

1. Hand off to `@agdt.git-save-work` to save work with a commit message.

## Expected Outcome

Changes are committed and pushed as needed.

## Next Step

Continue to pull request.
