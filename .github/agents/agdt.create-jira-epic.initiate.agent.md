---
description: "Create Jira Epic - Initiate: Create a new Jira epic"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Start the create-jira-epic workflow and capture epic details.

## Prerequisites

- **Required state**: `jira.project_key`, `jira.summary`, `jira.epic_name`
- **Set state** (if not already set):

  ```bash
  agdt-set jira.project_key <value>
  agdt-set jira.summary <value>
  agdt-set jira.epic_name <value>
  ```

## Actions

1. Initiate epic creation:

   ```bash
   agdt-initiate-create-jira-epic-workflow
   ```

## Expected Outcome

A Jira epic is created or the workflow is ready for inputs.

## Next Step

Workflow is complete.
