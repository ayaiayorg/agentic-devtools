# Feature Specification: SpecKit Phase Mapping Enforcement

**Feature Branch**: `1198-speckit-phase-mapping-enforcement`
**Created**: 2026-04-15
**Status**: Draft
**Input**: User description: "Require phase mapping table when plan and tasks use different numbering"
**Source Issue**: #1198 (<https://github.com/ayaiayorg/agentic-devtools/issues/1198>)

## Clarifications

### Session 2026-04-28

- Q: The tasks template (`tasks-template.md`) does not currently have a "User Story Mapping" section — where exactly should the Phase Mapping table placeholder be placed in the template? → A: The
  Phase Mapping table placeholder should be placed immediately after the "Path Conventions" section (and its closing HTML comment block) and before the "Phase 1: Setup" heading. If a User Story
  Mapping section is added in the future, the Phase Mapping table follows it. The FR-003 placement rule ("after any User Story Mapping section") remains correct as a forward-compatible instruction for
  generated `tasks.md` files, while the template placement is anchored to the existing structure.

- Q: FR-005 requires the template to always include a Phase Mapping placeholder, but FR-001 says the table is only required "when the task phases use different numbering." Should the template
  placeholder be unconditional (always present in template with a conditional-inclusion comment) or conditional? → A: The template placeholder is unconditional — it is always present in
  `tasks-template.md` as a structural example with an HTML comment explaining when the LLM should populate vs. omit it. The generation prompt (FR-001) instructs the LLM to populate the table when
  phases differ and to either omit it or include a single-line "phases are aligned" note when they match.

- Q: Since this feature targets LLM prompt guidance (not programmatic validation), how should the `speckit.analyze` agent determine whether phases "differ" between plan.md and tasks.md — by phase
  count alone, by heading text comparison, or by semantic assessment? → A: The analyze agent uses LLM-based semantic assessment (consistent with all other analyze checks). It compares phase headings
  and counts between `plan.md` and `tasks.md`. Phases are considered "different" when either (a) the phase count differs, or (b) the phase headings indicate different organizational schemes (e.g.,
  domain-driven vs. story-driven). This is an LLM judgment call, not a programmatic string comparison, matching the existing analyze agent design.

- Q: The spec references the agent file as `speckit.tasks.agent.md` and the command template as `.specify/templates/commands/tasks.md` — should the Phase Mapping instruction also be added to the CLI
  command template at `.specify/templates/commands/tasks.md` (step 4, "Generate tasks.md") in addition to the agent file, since both are used depending on invocation path? → A: Yes, both files must be
  updated. FR-009 already requires this ("present in both the GitHub agent file and the CLI command template"). The agent file (`.github/agents/speckit.tasks.agent.md`) is used by VS Code Copilot Chat
  `/speckit.tasks`, while the CLI command template (`.specify/templates/commands/tasks.md`) is used by the CLI invocation. Both must contain the Phase Mapping instruction for consistency.

- Q: For the edge case where `plan.md` has no explicit phase headings, should the Phase Mapping table reference plan section headings verbatim (e.g., "§ Design Overview") or should it use a normalized
  label format? → A: The Phase Mapping table should reference plan section headings verbatim as they appear in `plan.md` (e.g., "Design Overview", "Integration Layer"). No normalization prefix like
  "§" is required. This preserves traceability — the reader can search for the exact heading in `plan.md`. The edge case section has been updated to reflect this.

## Problem Statement

All three recent SpecKit PRs (#1009, #1177, #1178) exhibited phase numbering mismatches between `plan.md` and `tasks.md`.
The root cause is a structural divergence: `plan.md` organizes work into implementation phases
(e.g., Phase 1: Core Module, Phase 2: Integration), while `tasks.md` reorganizes that work by user story
(Phase 1: Setup, Phase 2: Foundational, Phase 3+: User Stories). This reorganization is by design —
it enables independent, MVP-first delivery — but without an explicit cross-reference,
readers cannot trace how plan phases map to task phases.

PR #1009 eventually resolved this by adding a "Phase Mapping: Plan → Tasks" table at the top of `tasks.md`
(flagged as F03 in analysis). PR #1177 also added one after analysis flagged it (F08).
These ad-hoc fixes prove the pattern works, but the fix should be built into the generation prompts
so it is always present rather than discovered post-hoc by `/speckit.analyze`.

## Scope

**In scope:**

- Updating the `speckit.tasks` generation prompts to mandate a Phase Mapping table
  in `tasks.md` when phase numbering differs from `plan.md`
  - Both the GitHub agent file (`.github/agents/speckit.tasks.agent.md`) and
    the CLI command template (`.specify/templates/commands/tasks.md`) must be updated
- Updating the `speckit.analyze` detection rules to explicitly flag missing phase mapping
  as a finding (using LLM-based semantic assessment of phase headings and counts,
  consistent with the existing analyze agent design)
- Updating the `tasks-template.md` (`.specify/templates/tasks-template.md`) to include
  a Phase Mapping table placeholder positioned after the "Path Conventions" section
  and before the "Phase 1: Setup" heading

**Out of scope:**

- Enforcing identical phase numbering between `plan.md` and `tasks.md`
  (the current user-story-based reorganization in tasks is a deliberate design choice)
- Changes to `plan.md` generation or the `speckit.plan` prompts
  (the plan's phase structure is domain-driven and should not be constrained)
- Automated validation tooling
  (e.g., a script that parses both files and compares phase numbers)

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Phase Mapping Table Auto-Generated in tasks.md (Priority: P1)

As a developer generating a `tasks.md` from a `plan.md` via `/speckit.tasks`,
I want the task generation to automatically include a "Phase Mapping: Plan → Tasks" table
near the top of `tasks.md`, after any User Story Mapping section, whenever the task phases differ from the plan phases,
so that I can trace every task phase back to its originating plan phase
without manual cross-referencing.

**Why this priority**: This is the core behavior change. It eliminates the root cause —
the mapping table is generated proactively instead of being discovered as a deficiency
during `/speckit.analyze`. Every subsequent SpecKit run benefits immediately.

**Independent Test**: Can be fully tested by running `/speckit.tasks` against any
`plan.md` + `spec.md` pair where the plan and task phase structures differ —
either in count (M ≠ N) or in numbering/semantics (e.g., domain-driven vs.
story-driven phases) — then verifying the output `tasks.md` contains a correctly
structured Phase Mapping table.

**Acceptance Scenarios**:

1. **Given** a `plan.md` with 5 implementation phases and a `spec.md` with 3 user stories,
   **When** `/speckit.tasks` generates `tasks.md`,
   **Then** `tasks.md` contains a "Phase Mapping: Plan → Tasks" table placed after the User Story Mapping section
   and before the first phase heading, with one row per task phase mapping it to the corresponding plan phase(s).

2. **Given** a `plan.md` with 4 implementation phases and a `spec.md` with 1 user story
   (producing tasks phases: Setup, Foundational, US1, Polish — 4 phases matching plan count
   but with different semantics),
   **When** `/speckit.tasks` generates `tasks.md`,
   **Then** `tasks.md` still contains a Phase Mapping table because the numbering schemes differ
   (plan phases are domain-driven, task phases are story-driven).

3. **Given** a `plan.md` whose phases map 1:1 in both number and semantic content
   to the generated task phases,
   **When** `/speckit.tasks` generates `tasks.md`,
   **Then** the Phase Mapping table MAY be omitted or MAY include a single-sentence note
   stating that phases are aligned.

4. **Given** a plan phase that maps to multiple task phases
   (e.g., plan Phase 1 splits into task Phase 1: Setup and Phase 2: Foundational),
   **When** the mapping table is generated,
   **Then** each of those task phase rows references the same plan phase
   (e.g., task Phase 1 → Plan Phase 1, task Phase 2 → Plan Phase 1).

5. **Given** a task phase that draws from multiple plan phases
   (e.g., task Phase 6: Polish draws from plan Phases 4 and 5),
   **When** the mapping table is generated,
   **Then** the task phase row lists all corresponding plan phases (e.g., "Phase 4, 5").

---

### User Story 2 — Tasks Template Includes Phase Mapping Placeholder (Priority: P2)

As a SpecKit maintainer, I want the `tasks-template.md` to include a Phase Mapping table
placeholder section with format guidance, so that the template itself documents the expectation
and the LLM has a concrete structural example to follow during generation.

**Why this priority**: The template is the structural contract for all generated `tasks.md` files.
Adding the placeholder ensures consistency across all features and makes the expectation explicit
for both human and AI consumers of the template.

**Independent Test**: Can be verified by inspecting `tasks-template.md` for the presence
of a Phase Mapping section with the correct table format and guidance comments.

**Acceptance Scenarios**:

1. **Given** the current `tasks-template.md` without a Phase Mapping section,
   **When** this feature is implemented,
   **Then** `tasks-template.md` contains a "Phase Mapping: Plan → Tasks" section positioned
   after the "Path Conventions" section (and its closing HTML comment block) and before
   "Phase 1: Setup", with a table showing the expected column headers
   (`Tasks Phase`, `Plan Phase(s)`, `Description`) and example rows.

2. **Given** the updated `tasks-template.md`,
   **When** a developer reads the template,
   **Then** the section includes an HTML comment explaining when the table is required
   (always when phase numbering or organizational scheme differs) and when it may be
   omitted (only when phases are 1:1 aligned in both count and semantics).

---

### User Story 3 — Analyze Agent Flags Missing Phase Mapping (Priority: P2)

As a developer running `/speckit.analyze` on a feature's artifacts,
I want the analyzer to explicitly check for and flag a missing Phase Mapping table
when `plan.md` and `tasks.md` use different phase numbering,
so that the mismatch is caught systematically rather than relying on ad-hoc reviewer judgment.

**Why this priority**: This is a defense-in-depth measure. Even with the prompt update (US1),
LLMs may occasionally omit the table. The analyze pass provides a safety net.
It has the same priority as US2 because both reinforce the core behavior.

**Detection heuristic**: The analyze agent uses LLM-based semantic assessment (consistent
with all other analyze checks). Phases are considered "different" when either (a) the phase
count differs between `plan.md` and `tasks.md`, or (b) the phase headings indicate different
organizational schemes (e.g., domain-driven vs. story-driven). This is an LLM judgment call,
not a programmatic string comparison.

**Independent Test**: Can be tested by running `/speckit.analyze` against a `tasks.md`
that has different phase numbering from its `plan.md` but lacks a Phase Mapping table,
and verifying a finding is emitted.

**Acceptance Scenarios**:

1. **Given** a `plan.md` with 5 phases and a `tasks.md` with 10 phases and no Phase Mapping table,
   **When** `/speckit.analyze` runs,
   **Then** it produces a finding with category "F. Inconsistency", severity "HIGH",
   and a recommendation to add a Phase Mapping table.

2. **Given** a `plan.md` with 5 phases and a `tasks.md` with 10 phases
   that includes a correctly structured Phase Mapping table,
   **When** `/speckit.analyze` runs,
   **Then** no phase-mapping-related finding is produced.

3. **Given** a `tasks.md` with a Phase Mapping table that references a plan phase
   not present in `plan.md` (e.g., table mentions "Plan Phase 6" but plan only has 5 phases),
   **When** `/speckit.analyze` runs,
   **Then** it produces a finding with category "F. Inconsistency", severity "MEDIUM",
   noting the stale/incorrect mapping reference.

---

### User Story 4 — Task Generation Prompt Documents Phase Mapping Requirement (Priority: P3)

As a SpecKit maintainer updating or reviewing the task generation prompts,
I want the `speckit.tasks` agent instructions and the
`.specify/templates/commands/tasks.md` command template to explicitly document the
Phase Mapping requirement with examples, so that the instruction is durable across
prompt revisions and clearly understood by any LLM following the prompt.

**Why this priority**: This is an instructional/documentation concern.
The prompt text is the mechanism that delivers US1, but it is lower priority because
the template (US2) already provides structural guidance.
This story ensures the behavioral instruction is also explicit in the command flow.

**Independent Test**: Can be verified by reading the updated `speckit.tasks.agent.md`
and `.specify/templates/commands/tasks.md` for the presence of Phase Mapping instructions.

**Acceptance Scenarios**:

1. **Given** the current `speckit.tasks.agent.md` agent file
   (`.github/agents/speckit.tasks.agent.md`),
   **When** this feature is implemented,
   **Then** the "Phase Structure" section includes a rule stating:
   "If the task list uses different phase numbering than the plan, include a Phase Mapping table
   at the top of tasks.md that maps each task phase to its corresponding plan phase(s)."

2. **Given** the current `.specify/templates/commands/tasks.md` command template,
   **When** this feature is implemented,
   **Then** step 4 ("Generate tasks.md") includes the Phase Mapping table
   as a required output element.

3. **Given** the updated prompts,
   **When** a developer reads the Phase Mapping instruction,
   **Then** the instruction includes at least one concrete example table
   showing the expected format.

---

### Edge Cases

- **What happens when `plan.md` has no explicit phase headings?**
  The Phase Mapping table should still be generated if the tasks file has multiple phases.
  The "Plan Phase(s)" column should reference the relevant plan section headings verbatim
  as they appear in `plan.md` (e.g., "Design Overview", "Integration Layer") rather than
  numbered phases. This preserves traceability — the reader can search for the exact
  heading in `plan.md`.

- **What happens when the plan uses sub-phases (e.g., Phase 1a, 1b, 1c)?**
  The mapping table should reference sub-phases at the granularity used in the plan
  (e.g., "Phase 1a, 1b" not just "Phase 1").

- **How does the system handle a plan.md that is reorganized after tasks.md is generated?**
  The Phase Mapping table becomes stale. `/speckit.analyze` should flag stale references
  (US3, scenario 3). Regenerating tasks via `/speckit.tasks` produces a fresh mapping.

- **What happens if the LLM omits the Phase Mapping table despite the prompt instruction?**
  `/speckit.analyze` catches this (US3) and recommends adding the table
  before proceeding to `/speckit.implement`.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The `speckit.tasks` generation prompts MUST instruct the LLM to include
  a "Phase Mapping: Plan → Tasks" table in `tasks.md` when the task phases use different
  numbering or organization than the plan phases. Phases are considered "different" when
  either the phase count differs or the phase headings indicate different organizational
  schemes (e.g., domain-driven vs. story-driven).

- **FR-002**: The Phase Mapping table MUST use three columns:
  `Tasks Phase`, `Plan Phase(s)`, and `Description`.

- **FR-003**: The Phase Mapping table MUST be placed in `tasks.md` after any
  User Story Mapping section and before the first phase heading (Phase 1: Setup).
  In the template (`tasks-template.md`), the placeholder is positioned after the
  "Path Conventions" section and before "Phase 1: Setup".

- **FR-004**: Each row in the Phase Mapping table MUST map exactly one task phase
  to one or more plan phases, using the plan's own phase numbering or heading names
  verbatim as they appear in `plan.md`.

- **FR-005**: The `tasks-template.md` MUST include an unconditional Phase Mapping
  section with placeholder rows demonstrating the expected format and an HTML comment
  explaining when the LLM should populate the table vs. omit it in generated output.

- **FR-006**: The `speckit.analyze` detection rules MUST include a check for missing
  Phase Mapping tables when `plan.md` and `tasks.md` phase structures differ,
  using LLM-based semantic assessment of phase headings and counts.

- **FR-007**: The `speckit.analyze` agent MUST classify a missing Phase Mapping table
  as severity "HIGH" under category "F. Inconsistency".

- **FR-008**: The `speckit.analyze` agent MUST validate that plan phases referenced
  in the Phase Mapping table actually exist in `plan.md`,
  flagging stale references as severity "MEDIUM".

- **FR-009**: The Phase Mapping instruction MUST be present in both the GitHub agent file
  (`.github/agents/speckit.tasks.agent.md`) and the CLI command template
  (`.specify/templates/commands/tasks.md`) to ensure consistency across invocation paths.

- **FR-010**: The `speckit.tasks` prompts MUST include at least one concrete example
  of a correctly formatted Phase Mapping table.

### Non-Functional Requirements

- **NFR-001**: Prompt changes MUST NOT increase the total token count
  of the `speckit.tasks` agent by more than 500 tokens
  (estimated ~300-400 words of added instruction and example).

- **NFR-002**: The Phase Mapping table format MUST be consistent with existing table formats
  already used in `tasks.md` (markdown pipe tables with header separator row).

- **NFR-003**: All prompt and template changes MUST pass existing markdownlint checks
  without introducing new violations.

### Key Entities

- **Phase Mapping Table**: A markdown table in `tasks.md` that cross-references task phases
  to plan phases. Contains columns for task phase identifier, corresponding plan phase(s),
  and a brief description. Serves as the traceability bridge between the two artifacts.
  The template includes an unconditional placeholder; the generated output populates or omits
  it based on whether phases differ.

- **Task Phase**: A numbered section in `tasks.md` organizing tasks by execution stage
  (Setup → Foundational → User Stories → Polish).
  Numbering is determined by the user story count in `spec.md`.

- **Plan Phase**: A numbered section in `plan.md` organizing implementation work
  by domain concern (e.g., Core Module, Integration, Testing).
  Numbering is determined by the feature's technical architecture.
  When `plan.md` uses section headings instead of numbered phases, those headings
  are referenced verbatim in the Phase Mapping table.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of `tasks.md` files generated by `/speckit.tasks` after this change
  include a Phase Mapping table when the plan and task phase numbering or organization
  differs (including cases where counts match but semantics differ).

- **SC-002**: `/speckit.analyze` detects and reports a missing Phase Mapping table
  in all test cases where plan and task phases diverge, with zero false negatives.

- **SC-003**: The phase mapping findings (F03 in #1009, F08 in #1177, F13 in #1178)
  that were previously flagged ad-hoc by analysis are eliminated for all future SpecKit runs
  because the table is generated proactively.

- **SC-004**: No existing SpecKit tests or validation scripts are broken
  by the prompt and template changes.

- **SC-005**: The prompt additions are self-contained and do not require changes to any
  Python source code, shell scripts, or CI workflows —
  only markdown prompt/template files are modified.

---
*Generated by Copilot SDK (claude-opus-4.6)*
