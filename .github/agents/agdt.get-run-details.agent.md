---
description: "Get Run Details: Retrieve pipeline run details"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Retrieve details of a pipeline or build run in Azure DevOps.

## Prerequisites

- **Required state**: `run_id`
- **Set state** (if not already set):

  ```bash
  agdt-set run_id <value>
  ```

## Actions

1. Run the command:

   ```bash
   agdt-get-run-details
   ```

## Expected Outcome

Run details are retrieved and saved to an output file (background task).

## Next Step

Command is complete.
