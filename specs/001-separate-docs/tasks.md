# Tasks: Separate AGDT and Specify Documentation

**Input**: Design documents from `/specs/001-separate-docs/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Heuristic validation required (documentation review + checklist) per NFR-004.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish documentation inventory and scope

- [x] T001 Create documentation inventory table in specs/001-separate-docs/research.md (pages/sections → audience)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish shared labeling conventions and entry-point framing

- [x] T002 Define audience label conventions in SPEC_DRIVEN_DEVELOPMENT.md (e.g., “Developer-only”)
- [x] T003 Add end-user audience statement in README.md (explicitly end-user focused)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Find AGDT End‑User Documentation (Priority: P1) 🎯 MVP

**Goal**: End users land on README.md and see only AGDT usage guidance.

**Independent Test**: Open README.md and confirm no Specify references and end-user navigation only.

### Implementation for User Story 1

- [x] T004 [US1] Rework README.md to remove SDD/Specify content and focus on AGDT end-user usage
- [x] T005 [US1] Record README.md end-user validation notes in specs/001-separate-docs/quickstart.md

**Checkpoint**: User Story 1 is complete and independently verifiable

---

## Phase 4: User Story 2 - Find Specify Developer Documentation (Priority: P2)

**Goal**: Developers can find Specify guidance in SPEC_DRIVEN_DEVELOPMENT.md with clear developer framing.

**Independent Test**: Open SPEC_DRIVEN_DEVELOPMENT.md and confirm it is labeled for developers and contains the SDD workflow.

### Implementation for User Story 2

- [x] T006 [US2] Add a developer-only header/intro in SPEC_DRIVEN_DEVELOPMENT.md that states the audience and purpose
- [x] T007 [US2] Move SDD workflow and command guidance from README.md into SPEC_DRIVEN_DEVELOPMENT.md
- [x] T008 [P] [US2] Update specs/README.md with a developer-only audience label and a labeled link to SPEC_DRIVEN_DEVELOPMENT.md

**Checkpoint**: User Story 2 is complete and independently verifiable

---

## Phase 5: User Story 3 - Clear Documentation Boundaries (Priority: P3)

**Goal**: Maintainers have clear rules to keep end-user and developer content separated.

**Independent Test**: Review boundary rules and cross-links for explicit audience labels.

### Implementation for User Story 3

- [x] T009 [US3] Add a “Documentation Boundaries” section in SPEC_DRIVEN_DEVELOPMENT.md with placement rules
- [x] T010 [US3] Add cross-link audience labels in SPEC_DRIVEN_DEVELOPMENT.md wherever it references end-user docs

**Checkpoint**: User Story 3 is complete and independently verifiable

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final review and documentation consistency check

- [x] T011 [P] Perform heuristic documentation review and record results in specs/001-separate-docs/quickstart.md
- [x] T012 [P] Verify README.md contains no Specify references and record verification in specs/001-separate-docs/quickstart.md
- [x] T013 [P] Add documentation review checklist section in specs/001-separate-docs/quickstart.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: Depend on Foundational phase completion
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - no dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2); coordinate with US1 to avoid duplicate content during README→SPEC move
- **User Story 3 (P3)**: Can start after Foundational (Phase 2); should follow US2 to ensure boundary rules reflect final doc structure

### Within Each User Story

- Update entry points before documenting cross-links
- Move content before adding labels to avoid rework
- Story complete before moving to the next priority

### Parallel Opportunities

- T008 can run in parallel with T006/T007 (different files)
- T011 and T012 can run in parallel after all story tasks

---

## Parallel Example: User Story 2

```text
Task: "Add a developer-only header/intro in SPEC_DRIVEN_DEVELOPMENT.md"
Task: "Update specs/README.md with a developer-only audience label and a labeled link to SPEC_DRIVEN_DEVELOPMENT.md"
```

---

## Parallel Example: User Story 1

```text
Task: "Rework README.md to remove SDD/Specify content and focus on AGDT end-user usage"
Task: "Record README.md end-user validation notes in specs/001-separate-docs/quickstart.md"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Confirm README.md is end-user only and free of Specify references

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Validate end-user path (MVP)
3. Add User Story 2 → Validate developer path
4. Add User Story 3 → Validate boundary consistency
5. Finish Polish → Record heuristic review results

### Parallel Team Strategy

With multiple maintainers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Maintainer A: User Story 1 (README.md)
   - Maintainer B: User Story 2 (SPEC_DRIVEN_DEVELOPMENT.md)
   - Maintainer C: User Story 2 (specs/README.md)
3. Maintainer A/B coordinate boundary rules for User Story 3

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Documentation-only work; no automated tests required
- Record heuristic review notes per NFR-004
