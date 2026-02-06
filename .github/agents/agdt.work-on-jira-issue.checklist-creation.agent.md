---
description: "Work on Jira Issue - Checklist Creation: Create implementation checklist (step 5 of 11)"
handoffs:
  - label: "Continue to Implementation"
    agent: "agdt.work-on-jira-issue.implementation"
    prompt: "Implement checklist items."

---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Create the implementation checklist for the Jira issue.

## Prerequisites

- **Required state**: `jira.issue_key`
- **Set state** (if not already set):

  ```bash
  agdt-set jira.issue_key <value>
  ```

## Actions

1. Create the checklist:

   ```bash
   agdt-create-checklist
   ```

## Expected Outcome

A checklist is created and the workflow advances to implementation.

## Next Step

Continue to implementation.
