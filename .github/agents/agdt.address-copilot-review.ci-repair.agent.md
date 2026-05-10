---
description: "Address Copilot Review (CI Repair): Automatically address GitHub Copilot PR review comments and CI failures in a CI environment"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).
The expected input is a GitHub PR review comment URL of the form:
`https://github.com/{owner}/{repo}/pull/{pr_number}#pullrequestreview-{review_id}`

## Purpose

CI-safe variant of the address-copilot-review agent designed to run on a
GitHub-hosted runner within the AI PR Loop workflow. This agent:

- Addresses Copilot review comments and/or CI failures
- Applies lint fixes using only pinned trusted tooling (ruff, markdownlint-cli2)
- Commits and pushes changes
- Replies to review comments and resolves threads
- Re-requests Copilot review

**Scope limitations** (CI repair mode):

- Does NOT run tests (`agdt-test`, `pytest`, or any test runner)
- Does NOT install packages from the PR branch
- Does NOT execute PR-sourced scripts
- Does NOT approve or merge the PR

## Instructions

Follow the detailed instructions in the corresponding prompt file
(`.github/prompts/agdt.address-copilot-review.ci-repair.prompt.md`).

## Next Step

Task is complete.
