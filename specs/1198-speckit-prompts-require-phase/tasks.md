# Tasks: SpecKit Phase Mapping Enforcement

**Input**: Design documents from `/specs/1198-speckit-prompts-require-phase/`
**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Organization**: Tasks are grouped by user story to enable independent
implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- All changes target markdown prompt/template files only (SC-005)
- No Python, shell, or CI file changes required

## Phase Mapping: Plan → Tasks

<!-- Phase Mapping is required because the plan uses a 4-phase domain-driven
     structure while tasks use the standard story-driven structure (Setup →
     Foundational → User Stories → Polish). -->

| Tasks Phase | Plan Phase(s) | Description |
|---|---|---|
| Phase 1: Setup | — | No setup phase in plan; scaffolding not needed for prompt-only changes |
| Phase 2: Foundational | Phase 1: Template Update | Template is the structural contract referenced by generation prompts |
| Phase 3: US1 | Phase 2: Generation Prompt Updates | Core generation prompt changes that deliver auto-generated mapping tables |
| Phase 4: US2 | Phase 1: Template Update | Template placeholder section (already delivered in Phase 2 foundational) |
| Phase 5: US3 | Phase 3: Analyze Agent Update | Analyze agent detection rules for missing/stale phase mappings |
| Phase 6: US4 | Phase 2: Generation Prompt Updates | Prompt documentation and examples (reinforces Phase 3 changes) |
| Phase 7: Polish | Phase 4: Validation | Cross-cutting validation and PR readiness |

---

## Phase 1: Setup

**Purpose**: No project initialization needed — all changes are markdown file edits (SC-005)

- [ ] T001 Verify you are on the correct working branch for issue #1198

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The tasks template is the structural contract that both generation prompts reference. It must be updated first so that prompts can point to it as the authoritative example.

**⚠️ CRITICAL**: Generation prompt updates (US1, US4) reference the template structure, so this phase must complete first.

- [ ] T002 Insert a `## Phase Mapping: Plan → Tasks` section in `.specify/templates/tasks-template.md` positioned after the closing `-->` of the sample-tasks HTML comment block and before the
  `## Phase 1: Setup (Shared Infrastructure)` heading, satisfying FR-003 placement requirement and FR-005 unconditional placeholder requirement
- [ ] T003 Add a 3-column markdown table inside the new section with columns `Tasks Phase`, `Plan Phase(s)`, and `Description` (FR-002) containing 3 example rows demonstrating the expected format,
  plus a horizontal rule separator before Phase 1
- [ ] T004 Add an HTML comment block inside the Phase Mapping section explaining when the LLM should populate the table (phases differ in count or organizational scheme) vs. omit it (1:1 aligned),
  satisfying FR-005 guidance requirement

**Checkpoint**: Template now contains the Phase Mapping placeholder. Generation prompts can reference it.

---

## Phase 3: User Story 1 — Phase Mapping Table Auto-Generated in tasks.md (Priority: P1) 🎯 MVP

**Goal**: The `speckit.tasks` generation prompts automatically include a Phase Mapping table in `tasks.md` when task phases differ from plan phases.

**Independent Test**: Run `/speckit.tasks` against any `plan.md` + `spec.md` pair where plan and task phase structures differ, then verify the output `tasks.md` contains a correctly structured Phase
Mapping table.

### Implementation for User Story 1

- [ ] T005 [P] [US1] Add a `### Phase Mapping` subsection at the end of the existing `### Phase Structure` section in `.github/agents/speckit.tasks.agent.md` containing the FR-001 rule statement: "If
  the task list uses different phase numbering than the plan, include a Phase Mapping table at the top of tasks.md that maps each task phase to its corresponding plan phase(s)"
- [ ] T006 [P] [US1] Add a concrete example Phase Mapping table (3 rows minimum) inside the new `### Phase Mapping` subsection in `.github/agents/speckit.tasks.agent.md`, satisfying FR-010 example
  requirement
- [ ] T007 [P] [US1] Add an edge-case note in the `### Phase Mapping` subsection in `.github/agents/speckit.tasks.agent.md` for plans without numbered phases: reference plan section headings verbatim
  as they appear in `plan.md` (FR-004)
- [ ] T008 [US1] Add a bullet in step 4 of the `## Outline` section in `.github/agents/speckit.tasks.agent.md` requiring the Phase Mapping table as an output element when phases differ (FR-001,
  FR-009)
- [ ] T009 [P] [US1] Mirror the `### Phase Mapping` subsection (rule statement per FR-001, example table per FR-010, edge-case note per FR-004) at the end of `### Phase Structure` in
  `.specify/templates/commands/tasks.md`, satisfying FR-009 dual-path consistency
- [ ] T010 [US1] Add a bullet in step 4 of the `## Outline` section in `.specify/templates/commands/tasks.md` requiring the Phase Mapping table as an output element when phases differ (FR-009)

**Checkpoint**: Both invocation paths (agent + CLI) now instruct the LLM to generate Phase Mapping tables.

---

## Phase 4: User Story 2 — Tasks Template Includes Phase Mapping Placeholder (Priority: P2)

**Goal**: The `tasks-template.md` includes a Phase Mapping table placeholder section with format guidance.

**Independent Test**: Inspect `tasks-template.md` for the presence of a Phase Mapping section with correct table format and guidance comments.

### Implementation for User Story 2

- [ ] T011 [US2] Verify the Phase Mapping section added in T002–T004 satisfies all US2 acceptance scenarios: section is positioned after "Path Conventions" closing comment and before "Phase 1: Setup"
  (FR-003), table has correct column headers `Tasks Phase`, `Plan Phase(s)`, `Description` (FR-002), example rows are present, and HTML comment explains populate-vs-omit rules (FR-005)

**Checkpoint**: Template placeholder is complete and verified against all US2 acceptance criteria.

---

## Phase 5: User Story 3 — Analyze Agent Flags Missing Phase Mapping (Priority: P2)

**Goal**: `/speckit.analyze` detects and flags missing or stale Phase Mapping tables when plan and task phases differ.

**Independent Test**: Run `/speckit.analyze` against a `tasks.md` that has different phase numbering from its `plan.md` but lacks a Phase Mapping table, and verify a finding is emitted.

### Implementation for User Story 3

- [ ] T012 [US3] Add a bullet point under the `#### F. Inconsistency` section in `.github/agents/speckit.analyze.agent.md` for missing Phase Mapping table detection: when plan and tasks phase
  structures differ (count or organizational scheme per LLM semantic assessment) but `tasks.md` lacks a Phase Mapping table, emit severity HIGH under category "F. Inconsistency" with a recommendation
  to add one (FR-006, FR-007)
- [ ] T013 [US3] Add a second bullet point under `#### F. Inconsistency` in `.github/agents/speckit.analyze.agent.md` for stale Phase Mapping references: when the table references plan phases not
  present in `plan.md`, emit severity MEDIUM (FR-008)

**Checkpoint**: Analyze agent now detects both missing and stale Phase Mapping tables.

---

## Phase 6: User Story 4 — Task Generation Prompt Documents Phase Mapping Requirement (Priority: P3)

**Goal**: The `speckit.tasks` agent instructions and CLI command template explicitly document the Phase Mapping requirement with examples for durability across prompt revisions.

**Independent Test**: Read the updated `speckit.tasks.agent.md` and `.specify/templates/commands/tasks.md` for the presence of Phase Mapping instructions with examples.

### Implementation for User Story 4

- [ ] T014 [US4] Verify the Phase Mapping subsection added in T005–T010 satisfies all US4 acceptance scenarios: rule statement is present in `### Phase Structure` of
  `.github/agents/speckit.tasks.agent.md` (FR-001), step 4 bullet is present (FR-009), at least one concrete example table is included (FR-010), and the same content is mirrored in
  `.specify/templates/commands/tasks.md` (FR-009)

**Checkpoint**: Both prompt files are documented and verified against all US4 acceptance criteria.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validation, consistency checks, and PR readiness

- [ ] T015 Run markdownlint on all four modified files to verify no violations (NFR-003)
- [ ] T016 Run `bash scripts/run-pr-checks.sh` to verify all CI checks pass (SC-004)
- [ ] T017 Diff `.github/agents/speckit.tasks.agent.md` and `.specify/templates/commands/tasks.md` to verify the Phase Mapping subsections are consistent between agent and CLI paths (FR-009)
- [ ] T018 Estimate token delta for the two generation prompt files using `wc -w` (target ≤ ~385 words ≈ 500 tokens at ~1.3 words/token) to verify NFR-001 budget compliance
- [ ] T019 Verify no Python, shell, or CI files were modified (SC-005)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS generation prompt updates
- **US1 (Phase 3)**: Depends on Phase 2 (template must exist before prompts reference it)
- **US2 (Phase 4)**: Depends on Phase 2 (verification of template work done in Phase 2)
- **US3 (Phase 5)**: Depends on Phase 1 only — independent of Phases 2–4
- **US4 (Phase 6)**: Depends on Phase 3 (verification of prompt work done in Phase 3)
- **Polish (Phase 7)**: Depends on all previous phases

### Parallel Opportunities

- T005, T006, T007, T009 can run in parallel (different files or independent sections)
- Phase 5 (US3 — analyze agent) can run in parallel with Phase 3 (US1 — generation prompts)
- T011 and T014 are verification tasks and must run after their dependencies complete

### Within Each User Story

- Template changes before prompt changes (template is the structural contract)
- Agent file and CLI template can be edited in parallel (independent files)
- Verification tasks run last within each story

---
*Generated by Copilot SDK (claude-opus-4.6)*
