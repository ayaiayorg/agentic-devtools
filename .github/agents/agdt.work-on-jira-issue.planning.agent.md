---
description: "Work on Jira Issue - Planning: Analyze issue and post plan (step 4 of 11)"
handoffs:
  - label: "Continue to Checklist Creation"
    agent: "agdt.work-on-jira-issue.checklist-creation"
    prompt: "Create the implementation checklist."

---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Analyze the Jira issue and post a planning comment.

## Prerequisites

- **Required state**: `jira.issue_key`, `jira.comment`
- **Set state** (if not already set):

  ```bash
  agdt-set jira.issue_key <value>
  agdt-set jira.comment <value>
  ```

## Actions

1. Post the plan comment:

   ```bash
   agdt-add-jira-comment
   ```

## Expected Outcome

The plan is posted on the Jira issue and the workflow advances to checklist creation.

## Next Step

Continue to checklist creation.
