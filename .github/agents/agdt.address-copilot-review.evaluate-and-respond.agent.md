---
description: "Address Copilot Review (Evaluate and Respond): Evaluate review comments, make targeted changes, and post a structured resolution summary"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

The expected input is the body of the `@copilot` trigger comment posted on the PR, which
contains collapsible `<details>` blocks with review comment links (and any suppressed
comment excerpts), optional CI failure links, and a reference to this skill.

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
6. Commit and push. The post-push automation handles thread resolution, review re-request,
   and squashing.

**Scope limitations** (CI repair mode):

- Does NOT run the full test suite (`agdt-test`, `pytest`) — use only targeted
  `agdt-test-pattern` or `agdt-test-file` for verification.
- Does NOT install packages from the PR branch.
- Does NOT execute PR-sourced scripts.
- Does NOT approve or merge the PR.

**Copilot Cloud Agent Restrictions**:

- Cannot force-push (`git push --force`) — only regular `git push` is allowed.
- Cannot resolve PR review comment threads via UI/API.
- Cannot merge PRs.

**Pre-push Hook Behavior**:

Git hooks are pre-configured via `copilot-setup-steps.yml` — no manual setup needed.
After running `git push`, the pre-push hook automatically runs targeted checks (ruff format,
ruff check, per-file coverage, mypy, test structure validation). This can take up to
**2 minutes**. Do NOT interrupt the push or re-push during this time. If the push is
rejected because ruff reformatted files (look for "❌ Files were reformatted by ruff" in
the output or `.pre-push-output.log`), stage the reformatted files, amend the commit, and
push again.

You do NOT need to manually run `ruff format`, `ruff check`, or `mypy` before pushing.
The pre-push hook handles all of this automatically. Focus only on code changes that
address the review feedback.

## Instructions

Follow the detailed instructions in the corresponding prompt file
(`.github/prompts/agdt.address-copilot-review.evaluate-and-respond.prompt.md`).

## Next Step

Task is complete.
