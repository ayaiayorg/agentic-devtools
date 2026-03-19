---
description: agdt.vpn-status agent for checking VPN connection status.
---

# agdt.vpn-status

This Copilot agent checks and reports VPN connectivity status using `agentic-devtools` commands.

## Goal

Check and report the current VPN connectivity/status using the `agdt-vpn-status` command, which runs as a background task.

## Context

- All action commands (including `agdt-vpn-status`) run as background tasks and return immediately.
- To see results, you must query the background task using `agdt-task-status`, `agdt-task-log`, or `agdt-task-wait`.

## Actions

1. Run the VPN status check as a background task:

   ```bash
   agdt-vpn-status
   ```

   This will print a background task ID, for example:

   ```text
   Background task started: task-abc123
   ```

2. Wait for the VPN status task to complete and show its final log output:

   ```bash
   agdt-task-wait
   ```

   `agdt-vpn-status` automatically writes `background.task_id` to state.
   Manually set `background.task_id` only if you need to inspect a different task.

   If you only need to inspect the log without blocking, you can instead run:

   ```bash
   agdt-task-log
   ```

## Expected Outcome

- `agdt-vpn-status` starts a background task and prints a task ID (it does **not** print the VPN status directly).
- `agdt-task-wait` (or `agdt-task-log`) uses `background.task_id` to retrieve the background task log.
- The background task log output clearly indicates:
  - Whether the VPN is connected or disconnected.
  - Any relevant details such as VPN profile/name, connection endpoint, or detected issues (timeouts, authentication errors, etc.).
- If the VPN is disconnected or unhealthy, the log should provide enough information to describe the problem in natural language.
