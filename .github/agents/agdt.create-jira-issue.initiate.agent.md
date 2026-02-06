---
description: "Create Jira Issue - Initiate: Create a new Jira issue"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Start the create-jira-issue workflow and capture issue details.

## Prerequisites

- **Required state**: `jira.project_key`, `jira.summary`, `jira.description`
- **Set state** (if not already set):

  ```bash
  agdt-set jira.project_key <value>
  agdt-set jira.summary <value>
  agdt-set jira.description <value>
  ```

## Actions

1. Initiate issue creation:

   ```bash
   agdt-initiate-create-jira-issue-workflow
   ```

## Expected Outcome

A Jira issue is created or the workflow is ready for inputs.

## Next Step

Workflow is complete.
