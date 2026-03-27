---
description: "Address Copilot Review: Automatically address GitHub Copilot PR review comments by URL"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).
The expected input is a GitHub PR review comment URL of the form:
`https://github.com/{owner}/{repo}/pull/{pr_number}#pullrequestreview-{review_id}`

## Purpose

Automate the full end-to-end workflow for addressing Copilot PR review comments:
parse the review URL, fetch comments, triage, make code changes, reply, resolve
threads, and re-request Copilot review.

## Instructions

Follow the detailed instructions in the corresponding prompt file
(`.github/prompts/agdt.address-copilot-review.prompt.md`).

## Next Step

Task is complete.
