---
description: "Analyze Workflow: Perform deep code analysis with multi-identity log scanning, external worktree context, and parameterized scoping via --issue-key or --pr-id"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).
Expected input: a kebab-case workflow name, optionally followed by:

- `--issue-key <KEY>` — Scope analysis to a specific issue's worktree state
  (e.g. `--issue-key PROJECT-123`)
- `--pr-id <N>` — Scope analysis to a specific PR's worktree state
  (e.g. `--pr-id 42`)
- `--static-only` — Disable external worktree log scanning

`--issue-key` and `--pr-id` are mutually exclusive. When neither is provided,
the analysis uses the current bootstrap worktree key.

If no workflow name is provided, list available workflows and ask the user to
choose.

**Examples:**

```text
pull-request-review
work-on-jira-issue --issue-key PROJECT-123
pull-request-review --pr-id 42
work-on-jira-issue --static-only
```

## Purpose

Perform deep code analysis of any `agentic-devtools` workflow by following the
structured 8-step methodology defined in the `workflow-analysis` SKILL.md. The
agent reads the shared skill file, traces the workflow's full call graph, maps
state lifecycle, identifies async boundaries, enumerates failure modes, and
produces a structured JSON analysis file and a companion markdown report.

Enhanced capabilities:

- **Parameterized scoping** — use `--issue-key` or `--pr-id` to target a
  specific worktree's state and logs instead of relying on the current bootstrap
  context.
- **Multi-identity log scanning** — scans all identity directories under
  `.agdt/workflows/` for log evidence, attributing each entry with
  `[identity: {name}]` for traceability.
- **External worktree context** — collects read-only log evidence from external
  git worktrees sharing the same `.agdt/` root (disable with `--static-only`).
- **`external_context` output field** — structured external worktree evidence
  in the JSON output schema (`null` when static-only or no external worktrees).

## Instructions

Follow the detailed instructions in the corresponding prompt file
(`.github/prompts/agdt.analyze-workflow.prompt.md`).

## Next Step

Output files are ready for the **Create Issues from Analysis** agent
(`agdt.create-issues-from-analysis`, tracked in #1132) to convert findings
into actionable GitHub issues.
