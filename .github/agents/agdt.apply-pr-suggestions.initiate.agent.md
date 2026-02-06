---
description: "Apply PR Suggestions - Initiate: Apply PR review suggestions"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Start the apply PR suggestions workflow.

## Prerequisites

- **Required state**: `pull_request_id`
- **Set state** (if not already set):

  ```bash
  agdt-set pull_request_id <value>
  ```

## Actions

1. Initiate apply PR suggestions:

   ```bash
   agdt-initiate-apply-pr-suggestions-workflow
   ```

## Expected Outcome

The workflow starts and is ready to apply suggestions.

## Next Step

Workflow is complete.
