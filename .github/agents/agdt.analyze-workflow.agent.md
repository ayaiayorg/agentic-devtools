---
description: "Analyze Workflow: Perform deep code analysis of any agentic-devtools workflow to identify bugs, race conditions, and optimizations"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).
Expected input: a kebab-case workflow name (e.g. `pull-request-review`,
`work-on-jira-issue`). If no workflow name is provided, list available workflows
and ask the user to choose.

## Purpose

Perform deep code analysis of any `agentic-devtools` workflow by following the
structured 8-step methodology defined in the `workflow-analysis` SKILL.md. The
agent reads the shared skill file, traces the workflow's full call graph, maps
state lifecycle, identifies async boundaries, enumerates failure modes, and
produces a structured JSON analysis file and a companion markdown report.

## Instructions

Follow the detailed instructions in the corresponding prompt file
(`.github/prompts/agdt.analyze-workflow.prompt.md`).

## Next Step

Output files are ready for the **Create Issues from Analysis** agent
(`agdt.create-issues-from-analysis`, tracked in #1132) to convert findings
into actionable GitHub issues.
