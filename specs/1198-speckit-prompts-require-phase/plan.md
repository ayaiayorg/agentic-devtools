# Implementation Plan: SpecKit Phase Mapping Enforcement

**Issue**: [#1198](https://github.com/ayaiayorg/agentic-devtools/issues/1198)
**Branch**: `speckit/1198/phase-3-plan`

## Technical Context

- **Stack**: Markdown prompt/template files only — no Python, shell, or CI changes (SC-005)
- **Files to modify** (4 total):
  1. `.specify/templates/tasks-template.md` — add Phase Mapping placeholder section
  2. `.github/agents/speckit.tasks.agent.md` — add Phase Mapping generation rule + example
  3. `.specify/templates/commands/tasks.md` — mirror the same rule in the CLI command template
  4. `.github/agents/speckit.analyze.agent.md` — add missing-phase-mapping detection rule
- **Validation**: `bash scripts/run-pr-checks.sh` (markdownlint is the primary gate)

## Research Summary

Key decisions (derived from spec clarification sessions):

- **Placeholder format**: Always-present visible section (`## Phase Mapping: Plan → Tasks`) in the template with an internal
  HTML-comment guidance block; LLM populates or omits the table content at generation time
- **Analyze rule design**: LLM-based semantic assessment comparing phase headings/counts between `plan.md` and `tasks.md`
- **Token budget**: Prompt additions must stay within the 500-token budget (NFR-001); estimated ≤ 200 tokens total across all four files

## Design Overview

The change adds a single cross-reference table concept ("Phase Mapping: Plan → Tasks") to the SpecKit prompt chain at three enforcement points:

1. **Template** (structural contract) — an always-present placeholder with guidance comments
2. **Generation prompts** (behavioral instruction) — explicit rule + example in both agent and CLI paths
3. **Analyze agent** (safety net) — LLM-based semantic check under "F. Inconsistency"

No runtime code changes. The LLM is the "executor" — prompts are the only control surface.

## Implementation Phases

### Phase 1: Template Update (`tasks-template.md`)

**Deliverable**: Phase Mapping placeholder section in the template

**Tasks**:

1. Insert a new `## Phase Mapping: Plan → Tasks` section after the closing `-->` of the sample-tasks HTML comment block and before the `## Phase 1: Setup (Shared Infrastructure)` heading, containing:
   - An HTML comment block explaining when to populate vs. omit
   - A 3-column markdown table (`Tasks Phase`, `Plan Phase(s)`, `Description`) with 3 example rows
   - A horizontal rule separator before Phase 1

**Acceptance**: FR-002, FR-003, FR-005 satisfied. Template passes markdownlint.

### Phase 2: Generation Prompt Updates (agent + CLI command template)

**Deliverable**: Phase Mapping instruction in both invocation paths

**Tasks**:

1. In `.github/agents/speckit.tasks.agent.md`:
   - Add a `### Phase Mapping` subsection at the end of the existing `### Phase Structure` section with:
     - The rule statement (FR-001, FR-009)
     - A concrete example table (FR-010)
     - Edge case note for plans without numbered phases (FR-004)
   - In step 4 of the `## Outline` section, add a bullet requiring the Phase Mapping table as an output element

2. In `.specify/templates/commands/tasks.md`:
   - Mirror the same `### Phase Mapping` subsection at the end of `### Phase Structure`
   - In step 4 of the `## Outline` section, add the same bullet requiring the Phase Mapping table

**Acceptance**: FR-001, FR-004, FR-009, FR-010 satisfied. Both files pass markdownlint. Token delta ≤ 500 (NFR-001).

### Phase 3: Analyze Agent Update (`speckit.analyze.agent.md`)

**Deliverable**: Phase Mapping detection rules in the analyze agent

**Tasks**:

1. In `.github/agents/speckit.analyze.agent.md`, under the `#### F. Inconsistency` bullet list, add two new bullet points:
   - **Missing Phase Mapping table**: When plan and tasks phase structures differ (count or organizational scheme) but tasks.md lacks a Phase Mapping table → severity HIGH (FR-006, FR-007)
   - **Stale Phase Mapping references**: When the Phase Mapping table references plan phases not present in plan.md → severity MEDIUM (FR-008)

**Acceptance**: FR-006, FR-007, FR-008 satisfied. File passes markdownlint.

### Phase 4: Validation

**Tasks**:

1. Run `bash scripts/run-pr-checks.sh` — all checks must pass (SC-004, NFR-003)
2. Manually verify no Python/shell/CI files were touched (SC-005)
3. Estimate token delta for the two generation prompt files stays under 500 tokens (NFR-001)

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| LLM ignores the Phase Mapping instruction despite prompt update | Medium | Low | Analyze agent (Phase 3) catches omissions as a safety net |
| Prompt additions exceed 500-token budget (NFR-001) | Low | Low | Keep example table to 3 rows; reuse existing phrasing; measure with `wc -w` (~1.3 words/token) |
| markdownlint failures from new HTML comments or tables | Low | Medium | Run `markdownlint` locally before committing; use established table/comment patterns from existing template |
| Inconsistency between agent and CLI command template | Medium | Medium | Copy-paste the Phase Mapping subsection verbatim; diff the two files after editing |

## Dependencies

- **Internal**: No code dependencies — all changes are self-contained markdown edits
- **External**: None — no new tools, packages, or services required
- **Ordering**: Phase 1 (template) should land first since both generation prompts reference `tasks-template.md`; Phase 3 (analyze) is independent

---
*Generated by Copilot SDK (claude-opus-4.6)*
