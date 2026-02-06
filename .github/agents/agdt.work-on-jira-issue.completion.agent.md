---
description: "Work on Jira Issue - Completion: Post final Jira comment (step 11 of 11)"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Post the final Jira comment with completion details.

## Prerequisites

- **Required state**: `jira.issue_key`, `pull_request_id`, `jira.comment`
- **Set state** (if not already set):

  ```bash
  agdt-set jira.issue_key <value>
  agdt-set pull_request_id <value>
  agdt-set jira.comment <value>
  ```

## Actions

1. Post the completion comment:

   ```bash
   agdt-add-jira-comment
   ```

## Expected Outcome

The Jira issue is updated with the final comment.

## Next Step

Workflow is complete.
