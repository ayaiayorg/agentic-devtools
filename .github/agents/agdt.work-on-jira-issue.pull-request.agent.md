---
description: "Work on Jira Issue - Pull Request: Create a pull request (step 10 of 11)"
handoffs:
  - label: "Continue to Completion"
    agent: "agdt.work-on-jira-issue.completion"
    prompt: "Post the final Jira comment."

---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Create a pull request for the Jira issue work.

## Prerequisites

- **Required state**: `source_branch`, `title`
- **Set state** (if not already set):

  ```bash
  agdt-set source_branch <value>
  agdt-set title <value>
  ```

## Actions

1. Create the pull request:

   ```bash
   agdt-create-pull-request
   ```

## Expected Outcome

A pull request is created and the workflow advances to completion.

## Next Step

Continue to completion.
