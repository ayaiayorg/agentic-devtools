---
description: "Wait for Run: Start a background task to monitor a pipeline run"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Start a background task that monitors a pipeline or build run in Azure DevOps.
This command returns immediately with a task ID — it does **not** block.

## Prerequisites

- **Required state**: `run_id`
- **Set state** (if not already set):

  ```bash
  agdt-set run_id <value>
  ```

## Actions

1. Start the background monitoring task:

   ```bash
   agdt-wait-for-run
   ```

   Optional flags: `--run-id <ID>`, `--fetch-logs`, `--vpn-toggle`,
   `--poll-interval <seconds>`.

2. If you need to **block until the run completes**, follow up with:

   ```bash
   agdt-task-wait
   ```

## Expected Outcome

A background task is created that periodically polls the run status. The command
returns immediately with a task ID. Use `agdt-task-wait` to block until the
background task (and therefore the monitored run) completes.

## Next Step

Command is complete.
