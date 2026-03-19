---
description: "Multi-Model Review: Run multi-model review pipeline"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Run the `agdt-review` multi-model pull-request review pipeline using only implemented
subcommands and flags.

## Prerequisites

- **Required** (for `dispatch`): PR ID and a label
- **Required** (for `status`): PR ID
- **Required** (for `consolidate`): PR ID

## Actions

1. Dispatch a multi-model review:

   ```bash
   agdt-review dispatch --pr-id <PR_ID> --label <LABEL>
   ```

   Optional flags:
   - `--config-path <PATH>`
   - `--dry-run`

2. Check review status:

   ```bash
   agdt-review status --pr-id <PR_ID>
   ```

3. Consolidate review output:

   ```bash
   agdt-review consolidate --pr-id <PR_ID>
   ```

   Optional flag:
   - `--model-id <MODEL_ID>`

4. Read resolved review config:

   ```bash
   agdt-review config-get --config-path <PATH>
   ```

5. Validate review config:

   ```bash
   agdt-review config-validate --config-path <PATH>
   ```

6. Show help when needed:

   ```bash
   agdt-review --help
   ```

## Expected Outcome

- `dispatch` starts or plans a review run for the given PR and label.
- `status` returns current review progress for a PR.
- `consolidate` combines model outputs for a PR.
- `config-get` prints resolved configuration using `--config-path`.
- `config-validate` validates configuration using `--config-path`.
- `--run-id` and `--key` are not used because they are not supported by this CLI.

## Next Step

Command is complete.
