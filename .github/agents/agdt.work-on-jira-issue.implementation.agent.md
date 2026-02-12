---
description: "Work on Jira Issue - Implementation: Implement checklist items (step 6 of 11)"
handoffs:
  - label: "Continue to Implementation Review"
    agent: "agdt.work-on-jira-issue.implementation-review"
    prompt: "Review completed checklist items."

---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Implement the checklist items for the Jira issue.

## Prerequisites

- **Required state**: `jira.issue_key`
- **Set state** (if not already set):

  ```bash
  agdt-set jira.issue_key <value>
  ```

## Actions

1. Update checklist progress:

   ```bash
   agdt-update-checklist --completed <item-numbers>
   ```

2. Save work as needed:

   ```bash
   agdt-git-save-work
   ```

## Expected Outcome

Implementation work is completed and checklist progress is updated.

## Next Step

Continue to implementation review.
