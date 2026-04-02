---
description: "PR Merge Manager: Poll PR state, address Copilot review comments, approve and merge when green"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).
Expected input flags: `--pr <number>` (required), `--repo <owner/repo>` (optional,
defaults to the current repository), plus optional tuning flags `--max-iterations <number>`
and `--poll-interval <seconds>`. See `.github/prompts/agdt.pr-merge-manager.prompt.md`
for the full flag set.

## Purpose

Automate the repetitive PR completion loop: poll the PR and its latest Copilot review
for the current head commit, delegate to `/agdt.address-copilot-review` when feedback
exists, and approve then merge when all checks are green — repeating until the PR
reaches a terminal state (merged, closed, or locked).

## Instructions

Follow the detailed instructions in the corresponding prompt file
(`.github/prompts/agdt.pr-merge-manager.prompt.md`).

## Next Step

Task is complete when the PR is merged, closed, or blocked.
