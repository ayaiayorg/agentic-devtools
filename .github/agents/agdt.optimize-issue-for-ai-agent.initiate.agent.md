---
description: "Optimize Issue for AI Agent - Initiate: Optimize a Jira issue for AI agent consumption"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Start the optimize-issue-for-ai-agent workflow to rewrite a Jira issue for better AI agent processing.

## Prerequisites

- Jira issue key must be available from one of:
  - CLI flag: `--issue-key <JIRA_ISSUE_KEY>`
  - State key: `jira.issue_key`
- If neither is available, ask for an issue key (for example `DFLY-1234`).

## Actions

1. Prefer explicit invocation when you have the key:

  ```bash
  agdt-initiate-optimize-issue-for-ai-agent-workflow --issue-key <JIRA_ISSUE_KEY>
  ```

2. If `jira.issue_key` is already set in state, this parameterless form is valid:

  ```bash
  agdt-initiate-optimize-issue-for-ai-agent-workflow
  ```

## Expected Outcome

The workflow starts for the resolved issue key. The command accepts `--issue-key` when provided and otherwise falls back to `jira.issue_key` in state.

## Next Step

Command is complete.
