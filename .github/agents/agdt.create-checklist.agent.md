---
description: "Create Checklist: Create a workflow checklist"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Create a checklist for the current workflow from CLI arguments.

## Prerequisites

- The `work-on-jira-issue` workflow **MUST** be active (for example, at the checklist-creation/implementation step).
- Verify the active workflow with:

  ```bash
  agdt-get-workflow
  ```

## Actions

1. Decide on the checklist items based on the current Jira issue and implementation plan.
2. Create the checklist using **one** of the following options:

   **Option A — Pass items via CLI argument (preferred):**

   ```bash
   agdt-create-checklist "Implement domain model|Add tests|Update docs"
   ```

   **Option B — Use state key `checklist_items`:**

   ```bash
   agdt-set checklist_items "Implement domain model|Add tests|Update docs"
   agdt-create-checklist
   ```

## Expected Outcome

A checklist is created in the workflow state.

## Next Step

Command is complete.
