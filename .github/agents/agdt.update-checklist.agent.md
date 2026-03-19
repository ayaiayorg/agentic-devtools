---
description: "Update Checklist: Update checklist items in the active workflow"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Update the implementation checklist for the active `work-on-jira-issue` workflow.

## Prerequisites

- An active `work-on-jira-issue` workflow is **required**.
- The workflow must already have a checklist (created via `agdt-create-checklist`).
- Verify with:

  ```bash
  agdt-get-workflow
  agdt-show-checklist
  ```

## Actions

Use one of the supported flags depending on the intended operation:

- Mark items as complete:

  ```bash
  agdt-update-checklist --complete "1,2,3"
  ```

- Add a new item:

  ```bash
  agdt-update-checklist --add "New checklist item text"
  ```

- Remove items:

  ```bash
  agdt-update-checklist --remove "2,4"
  ```

- Revert items to incomplete:

  ```bash
  agdt-update-checklist --revert "1,2"
  ```

- Edit an existing item:

  ```bash
  agdt-update-checklist --edit "1:Updated item text"
  ```

> **Important:** Index lists must be a single comma-separated string in quotes.
> Do **not** use `--completed 1 2 3` — that syntax is invalid.

## Expected Outcome

Checklist items are updated. If all items become complete, the workflow
automatically advances to the next step.

## Next Step

Command is complete.
