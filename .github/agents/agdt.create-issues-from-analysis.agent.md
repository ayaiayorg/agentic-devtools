---
description: "Create Issues from Analysis: Create GitHub issues in bulk from a structured workflow analysis JSON file"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).
Expected input: a file path to a `*-analysis.json` file produced by
`agdt.analyze-workflow`. Optional flags: `--dry-run`, `--start-from <N>`.

## Purpose

Create GitHub issues in bulk from a structured workflow analysis JSON file
(output of `agdt.analyze-workflow`). The agent reads the analysis, validates
every finding against the SKILL.md JSON Schema, generates a well-structured
issue body for each finding, creates the issues via
`agdt-create-agdt-task-issue` in priority order, tracks the finding-ID →
issue-number mapping, and updates cross-references between cascade-related
issues.

## Instructions

Follow the detailed instructions in the corresponding prompt file
(`.github/prompts/agdt.create-issues-from-analysis.prompt.md`).

## Next Step

The issue mapping file (`issue-mapping-{workflow}.json`) is ready for batch
refinement of the created issues (tracked in #1133).

> **Note:** A `handoffs:` declaration to `agdt.refine-issues-batch` will be
> added to this agent once that target agent is implemented (#1133).
