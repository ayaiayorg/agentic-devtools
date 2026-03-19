---
description: "Show Checklist: Display current checklist"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Display the current implementation checklist with completion status for the
active `work-on-jira-issue` workflow.

## Prerequisites

- An active `work-on-jira-issue` workflow is **required** (the command exits
  with a non-zero status if no workflow is active).
- The workflow should already have a checklist (created via
  `agdt-create-checklist`). If no checklist exists, the command prints a
  message suggesting to create one.

## Actions

1. Run the command:

   ```bash
   agdt-show-checklist
   ```

## Expected Outcome

The checklist is printed to stdout with item numbers and completion status.

## Next Step

Command is complete.
