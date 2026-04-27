# Tasks: SpecKit Prompts — Semantic Anchors Instead of Hardcoded Line Numbers

**Input**: Design documents from spec and implementation plan
**Prerequisites**: spec.md (required), plan.md (required)

**Tests**: Not requested — this is a prompt-wording-only change with no runtime code.

**Organization**: Tasks grouped by user story; scope limited to 2 prompt files.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (no dependencies between tasks; this can include work on different files or independent read-only/validation work on the same file)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Baseline & Audit)

**Purpose**: Establish token baselines and confirm problem scope before making changes

- [ ] T001 Install tiktoken package for cl100k_base token measurement (`pip install tiktoken`)
- [ ] T002 [P] Measure and record cl100k_base token count for `.github/agents/speckit.tasks.agent.md` (pre-change baseline)
- [ ] T003 [P] Measure and record cl100k_base token count for `.specify/templates/tasks-template.md` (pre-change baseline)
- [ ] T004 Audit 3+ existing `tasks.md` files under `specs/` to catalogue hardcoded line-number reference patterns and confirm the problem scope

---

## Phase 2: Foundational (Compatibility Verification)

**Purpose**: Confirm the implement agent does not depend on line numbers — MUST complete before prompt edits

**⚠️ CRITICAL**: No prompt editing can begin until this phase confirms compatibility

- [ ] T005 Read `.github/agents/speckit.implement.agent.md` and confirm it uses search-based navigation (grep, glob, view) with no line-number-dependent logic —
  document findings as validation evidence for US4

**Checkpoint**: Implement-agent compatibility confirmed — prompt editing can now begin

---

## Phase 3: User Story 1 — Planner Emits Stable Task Locations (Priority: P1) 🎯 MVP

**Goal**: Update the agent prompt so generated tasks use semantic anchors instead of hardcoded line numbers

**Independent Test**: Generate a `tasks.md` from any spec and verify 0% bare line-number references in location descriptions

### Implementation for User Story 1

- [ ] T006 [US1] Add a "Location References" subsection inside the "Task Generation Rules" section of `.github/agents/speckit.tasks.agent.md` containing: a rule that tasks MUST use semantic anchors
  (not hardcoded line numbers); acceptable anchor types for code files (function/method/class names, constants, decorators, import blocks, test names, comment markers); acceptable anchor types for
  non-code files (headings, YAML/JSON key paths, table sections, bullet groups, recognizable text blocks); insertion-point guidance using "before/after/inside/under" a named landmark; cross-task
  reference guidance ("the helper introduced in Task N", "the `build_anchor` function created in the previous step"); disambiguation rule requiring surrounding context for ambiguous anchors; compact
  negative example (❌ `(line 73)`, `(~lines 42-57)`) and positive example (✅ `in the _execute_merge() function`, `under the ## Dependencies heading`)
- [ ] T007 [US1] Add a "Location References" guidance block to the Notes section of `.specify/templates/tasks-template.md` containing: a concise restatement that edit locations must use semantic
  anchors not line numbers; 2–3 before/after example transformations (one code file, one non-code file, one cross-task reference); edge-case guidance for ambiguous or missing anchors

**Checkpoint**: Both prompt files updated with semantic-anchor guidance — planner should now emit anchor-based tasks

---

## Phase 4: User Story 2 — Implementer Can Find Where to Change a File (Priority: P1)

**Goal**: Ensure task instructions point to meaningful file landmarks so implementers can apply changes correctly

**Independent Test**: Read generated tasks and verify each edit/insertion instruction references a semantic landmark, not a line number

### Implementation for User Story 2

- [ ] T008 [US2] Update sample task descriptions in the template's Phase 3+ example sections of `.specify/templates/tasks-template.md` to demonstrate semantic-anchor style where applicable (e.g.,
  replace generic `src/[location]/[file].py` patterns with anchor hints like "in the `UserService` class" or "under the `## Configuration` section")

**Checkpoint**: Template examples now model the anchor-based style for implementers

---

## Phase 5: User Story 3 — Reviewer Sees Consistent Terminology (Priority: P2)

**Goal**: Normalize all location-reference terminology to the single term "semantic anchor"

**Independent Test**: Search both files for legacy terms ("content-based anchor", "structural reference") — expect zero matches

### Implementation for User Story 3

- [ ] T009 [P] [US3] Ensure the term "semantic anchor" is used consistently throughout `.github/agents/speckit.tasks.agent.md` — remove or replace any occurrences of "content-based anchor", "structural
  reference", or other legacy location-reference terms
- [ ] T010 [P] [US3] Ensure the term "semantic anchor" is used consistently throughout `.specify/templates/tasks-template.md` — remove or replace any occurrences of "content-based anchor", "structural
  reference", or other legacy location-reference terms

**Checkpoint**: Unified terminology confirmed across both in-scope files

---

## Phase 6: User Story 4 — Validation: Implement Prompt Remains Compatible (Priority: P2)

**Goal**: Confirm, using the compatibility review already performed in T005, that semantic-anchor-based tasks work with the current implement agent without prompt changes

**Independent Test**: Verify that the evidence gathered in T005 shows `.github/agents/speckit.implement.agent.md` has no line-number-dependent parsing or logic
and therefore requires no changes for semantic-anchor-based tasks

### Validation for User Story 4

- [ ] T011 [US4] Document the implement-agent compatibility conclusion from T005 by recording that `.github/agents/speckit.implement.agent.md` contains no
  line-number-dependent logic, can process semantic-anchor-based tasks without modification, and therefore does not require an implement-agent prompt rewrite

**Checkpoint**: Implement-agent compatibility conclusion documented from T005 evidence — no changes needed to that file

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Token measurement, format validation, and final quality checks

- [ ] T012 [P] Measure cl100k_base token count for `.github/agents/speckit.tasks.agent.md` post-change and confirm it stays within the agent-file validation ceiling implied by the plan
  (~1,750 tokens, based on the measured baseline), not the looser ~1,841 estimate
- [ ] T013 [P] Measure cl100k_base token count for `.specify/templates/tasks-template.md` post-change and confirm this separately measured in-scope template stays within its own
  baseline-derived budget, with growth remaining modest and proportional rather than using the agent-file ceiling
- [ ] T014 [P] Run markdownlint on `.github/agents/speckit.tasks.agent.md` to ensure no formatting regressions
- [ ] T015 [P] Run markdownlint on `.specify/templates/tasks-template.md` to ensure no formatting regressions
- [ ] T016 Review 3 representative task-generation scenarios (existing-symbol edit, insertion relative to anchor, non-code file edit, cross-task reference) to confirm updated prompts would produce
  anchor-based output without bare line numbers
- [ ] T017 Final terminology sweep: grep both in-scope files for legacy terms ("content-based anchor", "structural reference") and for line-number-style location references, while allowing the
  explicit prohibition/example wording (for example, "anchors not line numbers" and negative examples such as `(line 73)` / `(~lines 42-57)`); confirm zero unintended matches

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user story work
- **User Story 1 (Phase 3)**: Depends on Foundational (Phase 2) — core prompt changes
- **User Story 2 (Phase 4)**: Depends on Phase 3 (T007 must exist before updating examples in same file)
- **User Story 3 (Phase 5)**: Can start after Phase 3 — terminology normalization
- **User Story 4 (Phase 6)**: Can start after Foundational (Phase 2) — validation only, no edits
- **Polish (Phase 7)**: Depends on all user story phases being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational — no dependencies on other stories
- **User Story 2 (P1)**: Depends on US1 (T007 adds the Notes block that T008 extends)
- **User Story 3 (P2)**: Can start after US1 — independent terminology sweep
- **User Story 4 (P2)**: Can start after Foundational — read-only validation

### Within Each User Story

- Read/audit before edit
- Agent file edits before template file edits (for US1, agent sets the standard)
- Terminology normalization after content additions

### Parallel Opportunities

- T002 and T003 can run in parallel (baseline measurement of different files)
- T009 and T010 can run in parallel (terminology sweep on different files)
- T012, T013, T014, T015 can all run in parallel (post-change measurement/linting on different files)
- US3 and US4 can run in parallel after US1 completes

---

## Parallel Example: Post-Change Validation

```text
# Launch all post-change measurements together:
Task T012: "Measure cl100k_base token count for speckit.tasks.agent.md"
Task T013: "Measure cl100k_base token count for tasks-template.md"
Task T014: "Run markdownlint on speckit.tasks.agent.md"
Task T015: "Run markdownlint on tasks-template.md"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (baseline measurement)
2. Complete Phase 2: Foundational (compatibility check)
3. Complete Phase 3: User Story 1 (core semantic-anchor guidance in both files)
4. **STOP and VALIDATE**: Confirm prompts produce anchor-based tasks, no line numbers
5. Measure token counts to ensure NFR-001 compliance

### Incremental Delivery

1. Setup + Foundational → Baselines established, compatibility confirmed
2. User Story 1 → Core anchor guidance in both files (MVP!)
3. User Story 2 → Template examples updated to model anchor style
4. User Story 3 → Terminology normalized across both files
5. User Story 4 → Implement-agent compatibility documented
6. Polish → Token counts verified, markdown linted, final sweep complete

---

## Notes

- [P] tasks = no dependencies between tasks (can include different files or independent work on the same file)
- [Story] label maps task to specific user story for traceability
- Only 2 files are edited: `.github/agents/speckit.tasks.agent.md` and `.specify/templates/tasks-template.md`
- `.github/agents/speckit.implement.agent.md` is read for validation only — never edited
- Token measurement uses OpenAI cl100k_base tokenizer (tiktoken)
- Save progress with `agdt-git-save-work`; after the first branch commit, subsequent saves should amend to preserve the single-commit-per-PR policy
- Stop at any checkpoint to validate independently

---
*Generated by Copilot SDK (claude-opus-4.6)*
