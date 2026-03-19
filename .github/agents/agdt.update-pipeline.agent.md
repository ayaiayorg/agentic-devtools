---
description: "Update Pipeline: Update an Azure DevOps pipeline"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Update an existing pipeline in Azure DevOps.

## Prerequisites

- Required state:
  - `pipeline.id`
- At least one update field must also be set:
  - `pipeline.new_name`, or
  - `pipeline.yaml_path`, or
  - `pipeline.new_folder_path`, or
  - `pipeline.description`

Example setup:

```bash
agdt-set pipeline.id 1234
agdt-set pipeline.new_name "Updated Pipeline Name"
```

## Actions

1. Run the command:

   ```bash
   agdt-update-pipeline
   ```

2. If you need to wait for completion, monitor the background task:

  ```bash
  agdt-task-status
  agdt-task-log
  agdt-task-wait
  ```

  `agdt-update-pipeline` automatically writes `background.task_id` to state.
  Manually set `background.task_id` only if you need to inspect a different task.

## Expected Outcome

The pipeline is updated (background task).

## Next Step

Command is complete.
