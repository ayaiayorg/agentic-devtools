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
and `--poll-interval <seconds>`. The `--max-iterations` and `--poll-interval` values are
used by the prompt to control the polling loop. See
`.github/prompts/agdt.pr-merge-manager.prompt.md` for the full flag set.

## Purpose

Automate the repetitive PR completion loop using `agdt-gh-*` commands, with
`agdt-gh-pr-poll-ready` as the primary orchestrator. It polls for merge readiness,
checking PR state, Copilot review status, and CI status under the hood via
`agdt-gh-pr-state`, `agdt-gh-copilot-review-status`, and
`agdt-gh-pr-checks-status`. Delegates to `/agdt.address-copilot-review`
when feedback exists, and approves with `agdt-gh-pr-approve` then merges with
`agdt-gh-pr-merge` when all checks are green — repeating until the PR reaches a
terminal state (merged, closed, or locked).

## Instructions

Follow the detailed instructions in the corresponding prompt file
(`.github/prompts/agdt.pr-merge-manager.prompt.md`).

## Next Step

Task is complete when the PR is merged, closed, or blocked.
