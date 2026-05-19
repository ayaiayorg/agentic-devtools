---
description: "Address Copilot Review (Evaluate and Respond): Evaluate review comments, make targeted changes, and post a structured resolution summary"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

The expected input is the body of the `@copilot` trigger comment posted on the PR, which
contains a structured list of review comment links (and any suppressed comment excerpts),
optional CI failure links, and a reference to this skill.

## Purpose

Orchestrate the full end-to-end workflow for addressing a GitHub Copilot PR review in a CI
environment:

1. Parse the structured trigger comment to extract the review link, per-comment links, and
   any CI failure info.
2. For each comment (visible and suppressed): read the comment body and surrounding code
   context, evaluate whether to implement, partially implement, or reject with rationale.
3. Make targeted code changes for accepted suggestions.
4. After all comments are processed, post a **single structured summary comment** on the PR.
5. If CI failures are listed, also address those (delegating to the CI repair sub-skill
   instructions).
6. Commit, push, reply to threads, resolve threads, and re-request Copilot review.

**Scope limitations** (CI repair mode):

- Does NOT run the full test suite (`agdt-test`, `pytest`) — use only targeted
  `agdt-test-pattern` or `agdt-test-file` for verification.
- Does NOT install packages from the PR branch.
- Does NOT execute PR-sourced scripts.
- Does NOT approve or merge the PR.

## Instructions

Follow the detailed instructions in the corresponding prompt file
(`.github/prompts/agdt.address-copilot-review.evaluate-and-respond.prompt.md`).

## Next Step

Task is complete.
