---
description: "VPN Run: Run a command with automatic VPN context management"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Run a shell command with automatic VPN context management. The command toggles
VPN on or off as needed before executing, then restores the previous state.

## Prerequisites

- A concrete command to execute (positional arguments — **required**).
- Optionally, a network requirement mode flag (`--require-vpn`,
  `--require-public`, or `--smart`). Defaults to `--smart` if omitted.

> **Important:** `agdt-vpn-run` with no positional command will fail with
> argparse usage output. Always provide a command.

## Actions

Choose the appropriate requirement mode and provide the command:

- **Run a command that requires VPN** (internal services like Jira, Azure DevOps):

  ```bash
  agdt-vpn-run --require-vpn <command> [args...]
  ```

- **Run a command that must avoid VPN** (public internet — npm, pip, GitHub):

  ```bash
  agdt-vpn-run --require-public <command> [args...]
  ```

- **Let the CLI decide** (auto-detect from command content):

  ```bash
  agdt-vpn-run --smart <command> [args...]
  ```

Examples:

```bash
agdt-vpn-run --require-vpn curl https://jira.swica.ch/rest/api/2/issue/DP-123
agdt-vpn-run --require-public npm install
agdt-vpn-run --smart az devops invoke ...
```

## Expected Outcome

The command executes with the correct VPN state, then the previous VPN state is
restored.

## Next Step

Command is complete.
