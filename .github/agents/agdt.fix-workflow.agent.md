---
description: "Fix Workflow: Diagnose and fix a bug in an agentic-devtools workflow command"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).
Expected input: a description of the failing command, observed behavior, expected behavior,
source repo path (where to run the command), test repo path (where to run repro during testing),
and test command (the integration-test command).

## Purpose

Investigate a reported bug in an `agentic-devtools` CLI workflow command, identify root cause,
implement a fix with tests, and deliver a PR — all while ensuring the pre-push hook passes
and the fix is verified end-to-end.

## Instructions

Follow the detailed instructions in the corresponding prompt file
(`.github/prompts/agdt.fix-workflow.prompt.md`).

The shared development lifecycle phases (implementation, push, integration test, delivery)
are defined in `.github/instructions/workflow-development.instructions.md`.

## Next Step

Task is complete when a PR is created and all artifacts are reported.
