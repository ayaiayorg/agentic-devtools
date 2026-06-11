---
description: "Test Workflow: Execute an agentic-devtools command, audit its behavior, and fix any findings"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).
Expected input: the CLI command to test, the repo path to run it from, and any relevant context.

## Purpose

Audit the behavior of an `agentic-devtools` CLI command by documenting expectations first,
executing and observing, identifying bugs/inefficiencies/improvements, then implementing
fixes and verifying with a clean rerun.

## Instructions

Follow the detailed instructions in the corresponding prompt file
(`.github/prompts/agdt.test-workflow.prompt.md`).

The shared development lifecycle phases (implementation, push, integration test, delivery)
are defined in `.github/instructions/workflow-development.instructions.md`.

## Important

**Do NOT execute the command until you have documented expectations and received user confirmation.**
The expectations document must be reviewed by a rubber duck subagent and presented to the user first.

## Next Step

Task is complete when a PR is created and the final clean rerun matches expectations.
