---
description: "Create Jira Subtask - Initiate: Create a Jira subtask"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Start the create-jira-subtask workflow and capture subtask details.

## Prerequisites

- **Required state**: `jira.parent_key`, `jira.summary`, `jira.description`
- **Set state** (if not already set):

  ```bash
  agdt-set jira.parent_key <value>
  agdt-set jira.summary <value>
  agdt-set jira.description <value>
  ```

## Actions

1. Initiate subtask creation:

   ```bash
   agdt-initiate-create-jira-subtask-workflow
   ```

## Expected Outcome

A Jira subtask is created or the workflow is ready for inputs.

## Next Step

Workflow is complete.
