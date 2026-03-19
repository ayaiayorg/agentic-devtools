---
description: "Release to PyPI: Publish package to PyPI"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Publish the agentic-devtools package to PyPI.

## Prerequisites

- Required state:
   - `pypi.package_name`
   - `pypi.version`

Example setup:

```bash
agdt-set pypi.package_name agentic-devtools
agdt-set pypi.version 1.2.3
```

## Actions

1. Run the command:

   ```bash
   agdt-release-pypi
   ```

2. If you need to wait for completion, monitor the background task:

   ```bash
   agdt-task-status
   agdt-task-log
   agdt-task-wait
   ```

   `agdt-release-pypi` automatically writes `background.task_id` to state.
   Manually set `background.task_id` only if you need to inspect a different task.

## Expected Outcome

The package is published to PyPI (background task).

## Next Step

Command is complete.
