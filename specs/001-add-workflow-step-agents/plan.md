# Implementation Plan: Workflow Step Chat Prompts

**Branch**: `001-add-workflow-step-agents` | **Date**: 2026-02-06 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from
`/specs/001-add-workflow-step-agents/spec.md`

## Summary

Add a VS Code Copilot Chat agent
(`.github/agents/agdt.<workflow>.<step>.agent.md`) and a delegation prompt
(`.github/prompts/agdt.<workflow>.<step>.prompt.md`) for every workflow step
defined in `agentic_devtools` — 21 steps across 7 workflows (11 + 5 multi-step,

5 single-step) = 42 new files plus a coverage verification script. This lets a

developer type `/agdt.work-on-jira-issue.planning` in the Copilot Chat window
to
developer type `/agdt.work-on-jira-issue.planning` in the Copilot Chat window
to
receive the same step-specific guidance that
`agdt-initiate-work-on-jira-issue-workflow` renders on the CLI, eliminating the
need to leave the editor. No Python runtime changes are required.

## Technical Context

**Language/Version**: Markdown (YAML frontmatter) for agents/prompts; Python
3.11 for optional coverage script
**Primary Dependencies**: VS Code Copilot Chat (agent `.agent.md` and prompt
`.prompt.md` conventions)
**Storage**: N/A — all artifacts are static Markdown files committed to the
repository
**Testing**: Manual smoke test in Copilot Chat; optional Python script to
verify
catalog completeness
**Target Platform**: VS Code (any OS) with GitHub Copilot extension  
**Project Type**: Single project (existing repository)  
**Performance Goals**: N/A — static files, no runtime  
**Constraints**: Agent files must be discoverable by VS Code within the
`.github/agents/` directory
**Scale/Scope**: 2 workflows × ~16 unique steps = ~30 agent+prompt file pairs +

5 single-step workflow agents

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
| ----------- | -------- | ------- |
| I. Auto-Approval Friendly Design | ✅ PASS | No CLI changes; agents invoke existing `agdt-*` commands |
| II. Single Source of Truth | ✅ PASS | Agents reference existing prompt templates via `agdt-*` CLI; no state duplication |
| III. Background Task Architecture | ✅ PASS | No new tasks; agents delegate to existing background commands |
| IV. Test-Driven Development & Coverage | ✅ PASS | Coverage script validates catalog completeness; existing tests unchanged |
| V. Code Quality & Maintainability | ✅ PASS | Consistent naming convention; no dead code |
| VI. User Experience Consistency | ✅ PASS | Naming mirrors existing `speckit.*` convention; step prompts share structure |
| VII. Performance & Responsiveness | ✅ PASS | Static Markdown files; no runtime cost |
| VIII. Python Package Best Practices | ✅ PASS | No changes to Python package; agents are repo-level Markdown |

**Gate result**: All principles satisfied. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/001-add-workflow-step-agents/
├── plan.md              # This file
├── research.md          # Phase 0: Agent/prompt pattern research
├── data-model.md        # Phase 1: Catalog of all workflow steps → agents
├── quickstart.md        # Phase 1: How to use & add new step agents
├── contracts/           # Phase 1: Agent file schema & naming contract
│   └── agent-schema.md
└── tasks.md             # Phase 2 (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
.github/
├── agents/
│   ├── speckit.*.agent.md           # Existing Speckit agents (unchanged)
│   ├── agdt.work-on-jira-issue.planning.agent.md         # NEW
│   ├── agdt.work-on-jira-issue.implementation.agent.md   # NEW
│   ├── agdt.work-on-jira-issue.<step>.agent.md           # NEW (one per step)
│   ├── agdt.pull-request-review.initiate.agent.md        # NEW
│   ├── agdt.pull-request-review.<step>.agent.md          # NEW (one per step)
│   ├── agdt.create-jira-issue.initiate.agent.md          # NEW
│   ├── agdt.create-jira-epic.initiate.agent.md           # NEW
│   ├── agdt.create-jira-subtask.initiate.agent.md        # NEW
│   ├── agdt.update-jira-issue.initiate.agent.md          # NEW
│   └── agdt.apply-pr-suggestions.initiate.agent.md       # NEW
├── prompts/
│   ├── speckit.*.prompt.md          # Existing Speckit prompts (unchanged)
│   ├── agdt.work-on-jira-issue.planning.prompt.md        # NEW
│   ├── agdt.work-on-jira-issue.<step>.prompt.md          # NEW (one per step)
│   ├── agdt.pull-request-review.<step>.prompt.md         # NEW (one per step)
│   ├── agdt.create-jira-issue.initiate.prompt.md         # NEW
│   └── ...                          # One prompt per agent
scripts/
└── verify-agent-coverage.py         # NEW: validates every step has agent+prompt
```

**Structure Decision**: Follows existing Speckit pattern
(`speckit.<name>.agent.md` + `speckit.<name>.prompt.md`). New files use
`agdt.<workflow>.<step>` namespace to avoid collision. No new Python package
modules, no `pyproject.toml` changes.

**Naming Exception**: The workflow `apply-pull-request-review-suggestions` uses
a shortened agent namespace `agdt.apply-pr-suggestions.*` to keep file names
manageable. The coverage script must map between the internal workflow name and
the shortened agent prefix. All other workflows use their full name as the
agent
namespace segment.

## Complexity Tracking

> No constitution violations. No complexity justifications needed.
