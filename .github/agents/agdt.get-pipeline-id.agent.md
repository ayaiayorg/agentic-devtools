---
description: "Get Pipeline ID: Retrieve a pipeline ID by name"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Retrieve a pipeline ID by name in Azure DevOps.

## Prerequisites

- Required state:
   - `pipeline.name`

Example setup:

```bash
agdt-set pipeline.name "My Pipeline Name"
```

## Actions

1. Run the command:

   ```bash
   agdt-get-pipeline-id
   ```

2. Optionally verify the result written to state:

   ```bash
   agdt-get pipeline.id
   ```

## Expected Outcome

The pipeline ID is retrieved (background task).

## Next Step

Command is complete.
