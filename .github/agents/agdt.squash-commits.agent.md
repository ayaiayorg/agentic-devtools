---
description: "Squash Commits: Squash multiple commits into a single well-formed commit"
---

## Copilot Cloud Agent Restriction

> **⚠️ This command is NOT supported in the Copilot Cloud Agent environment.**
> The squash-commits workflow rewrites git history and requires force-push.
> If you are a Copilot Cloud Agent, reject this request and inform the user:
> `The squash-commits workflow rewrites git history and requires force-push. Please run this command locally using VS Code Copilot Chat.`

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Guide squashing multiple commits on a feature branch into a single well-formed commit following repository conventions.

## Instructions

Follow the detailed instructions in the corresponding prompt file
(`.github/prompts/agdt.squash-commits.prompt.md`).

## Next Step

Task is complete.
