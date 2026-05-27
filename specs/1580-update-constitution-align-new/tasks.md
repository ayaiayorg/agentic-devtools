# Tasks: Update Constitution to v1.2.0

## Phase Mapping: Plan → Tasks

| Tasks Phase | Plan Phase(s) | Description |
|---|---|---|
| Phase 1: Setup | — | Read & orient (no direct plan equivalent) |
| Phase 2: Foundational | Plan Phase 1 | Sync Impact Report |
| Phase 3: US4 | Plan Phase 2 | Rewrite Principle I (Scoped Tool Availability) |
| Phase 4: US1 | Plan Phase 3 | Rewrite Principle II (Dual-Layer State) |
| Phase 5: US2 | Plan Phases 4, 8 | Update Principle IV + Quality Gates coverage |
| Phase 6: US5 | Plan Phase 6 (IX) | Add Principle IX (Graph Orchestration) |
| Phase 7: US6 | Plan Phase 6 (X) | Add Principle X (Dual-Engine) |
| Phase 8: US3 | Plan Phases 6 (XI), 7, 9 | Add Principle XI + update Dev Workflow + Governance |
| Phase 9: US7 | Plan Phase 1 (verify) | Verify Sync Impact Report completeness |
| Phase 10: US8 | Plan Phase 5 | Update Principle VI (remove version bump) |
| Phase 11: Version Footer | Plan Phase 10 | Update version footer |
| Final Phase | Plan Phase 11 | Verification & cross-cutting checks |

## Phase 1: Setup

- [ ] T001 Read current constitution structure and identify each semantic edit target in `.specify/memory/constitution.md`

## Phase 2: Foundational — Sync Impact Report

- [ ] T002 (FR-012) Replace the Sync Impact Report HTML comment block with a v1.1.0 → v1.2.0 change report listing modified principles (I, II, IV, VI), added principles (IX, X, XI), removed
  content, and templates requiring review in `.specify/memory/constitution.md`

## Phase 3: User Story 4 — Scoped Tool Availability (P1)

- [ ] T003 [US4] (FR-002) Rewrite Principle I: replace "Auto-Approval Friendly Design" under Principle I with "Scoped Tool Availability" describing explicit capability declarations per workflow step,
  acknowledging auto-approval as a transitional mechanism in `.specify/memory/constitution.md`
- [ ] T004 [US4] (FR-002) Verify happy-path: confirm Principle I title is "Scoped Tool Availability", describes explicit capability declarations per step, and acknowledges auto-approval as a
  transitional mechanism in `.specify/memory/constitution.md`

## Phase 4: User Story 1 — State Architecture (P1)

- [ ] T005 [US1] (FR-003) Rewrite Principle II: replace "Single Source of Truth" under Principle II with "Dual-Layer State Architecture" describing CLI parallel-safe JSON segments + LangGraph
  checkpointing, removing "No distributed configuration" in `.specify/memory/constitution.md`
- [ ] T006 [US1] (FR-003) Verify happy-path: confirm Principle II describes dual-layer state (CLI JSON segments + LangGraph checkpointing), references parallel-safe isolated state segments, and
  "No distributed configuration" does not appear in `.specify/memory/constitution.md`

## Phase 5: User Story 2 — Coverage 100% (P1)

- [ ] T007 [US2] (FR-004) Update Principle IV: change "Minimum 95% code coverage" to "100% code coverage" referencing ADR-011 in `.specify/memory/constitution.md`
- [ ] T008 [US2] (FR-011) Update Quality Gates → Pre-Commit: change "Code coverage ≥ 95% for changed files" to "Code coverage = 100% for changed files (per Principle IV and ADR-011)" in
  `.specify/memory/constitution.md`
- [ ] T009 [US2] (FR-004) Verify happy-path: confirm Principle IV states "100% code coverage" and references ADR-011, and zero occurrences of "95%" exist in `.specify/memory/constitution.md`
- [ ] T010 [US2] (FR-011) Verify happy-path: confirm Quality Gates → Pre-Commit states "Code coverage = 100% for changed files (per Principle IV and ADR-011)" in `.specify/memory/constitution.md`

## Phase 6: User Story 5 — Graph-Based Orchestration (P2)

- [ ] T011 [US5] (FR-006) Add new Principle IX "Graph-Based Workflow Orchestration" after Principle VIII describing graph-based orchestration with LangGraph as current implementation, checkpoint state
  recovery, and human-in-the-loop interrupts in `.specify/memory/constitution.md`
- [ ] T012 [US5] (FR-006) Verify: confirm Principle IX titled "Graph-Based Workflow Orchestration" exists, names LangGraph as current implementation, and mentions checkpoint recovery and
  human-in-the-loop interrupts in `.specify/memory/constitution.md`

## Phase 7: User Story 6 — Dual-Engine Compatibility (P2)

- [ ] T013 [US6] (FR-007) Add new Principle X "Dual-Engine Compatibility" after Principle IX describing opt-in routing (`--engine` flag) and fault isolation between engines in
  `.specify/memory/constitution.md`
- [ ] T014 [US6] (FR-007) Verify: confirm Principle X titled "Dual-Engine Compatibility" exists, requires opt-in routing for engine selection, and states failures in one engine must not affect the
  other in `.specify/memory/constitution.md`

## Phase 8: User Story 3 — Pre-1.0 Flexibility (P1)

- [ ] T015 [US3] (FR-008) Add new Principle XI "Pre-1.0 Flexibility" after Principle X codifying that breaking changes are allowed pre-1.0, no migration plans required, active removal of dead code in
  `.specify/memory/constitution.md`
- [ ] T016 [US3] (FR-009) Update Development Workflow → Code Changes: replace backward-compatibility requirement with "Breaking changes are permitted per Principle XI (Pre-1.0 Flexibility)"
  in `.specify/memory/constitution.md`
- [ ] T017 [US3] (FR-010) Update Governance → Amendments: remove "Migration plan for affected code" item and renumber remaining items in `.specify/memory/constitution.md`
- [ ] T018 [US3] (FR-008) Verify happy-path: confirm Principle XI titled "Pre-1.0 Flexibility" exists and states breaking changes are allowed pre-1.0 without migration plans in
  `.specify/memory/constitution.md`
- [ ] T019 [US3] (FR-009) Verify happy-path: confirm Development Workflow → Code Changes states "Breaking changes are permitted per Principle XI (Pre-1.0 Flexibility)" in
  `.specify/memory/constitution.md`
- [ ] T020 [US3] (FR-010) Verify happy-path: confirm "Migration plan for affected code" does not appear in Governance → Amendments in `.specify/memory/constitution.md`

## Phase 9: User Story 8 — UX Consistency Update (P3)

- [ ] T021 [US8] (FR-005) Update Principle VI: remove "Breaking changes to CLI UX require a major version bump and migration notes" and replace with reference to Principle XI in
  `.specify/memory/constitution.md`
- [ ] T022 [US8] (FR-005) Validate: confirm Principle VI no longer contains "Breaking changes to CLI UX require a major version bump and migration notes" and now includes a reference to Principle XI
  ("Pre-1.0 Flexibility") in `.specify/memory/constitution.md`

## Phase 10: User Story 7 — Sync Impact Report (P2)

- [ ] T023 [US7] (FR-012) Verify the Sync Impact Report (from T002) lists all modified principles (I, II, IV, VI), added principles (IX, X, XI), removed content, and templates requiring review —
  adjust if needed in `.specify/memory/constitution.md`

## Phase 11: Version Footer

- [ ] T024 (FR-001) Update version footer: change to `**Version**: 1.2.0 | **Ratified**: 2026-05-26 | **Last Amended**: 2026-05-26` in `.specify/memory/constitution.md`

## Final Phase: Verification & Cross-Cutting

- [ ] T025 Review SC-001 status — `**Version**: 1.2.0` is present in `.specify/memory/constitution.md`
- [ ] T026 Review SC-002 status — zero occurrences of "95%" remain in `.specify/memory/constitution.md`
- [ ] T027 Review SC-003 status — "No distributed configuration" is absent from `.specify/memory/constitution.md`
- [ ] T028 Review SC-004 status — "Breaking changes to CLI UX require a major version bump" is absent from `.specify/memory/constitution.md`
- [ ] T029 Review SC-005 status — "Migration plan for affected code" is absent from `.specify/memory/constitution.md`
- [ ] T030 Review SC-006 status — Principles IX, X, XI are present with correct titles in `.specify/memory/constitution.md`
- [ ] T031 Review SC-007 status — Sync Impact Report references `1.1.0 → 1.2.0` in `.specify/memory/constitution.md`
- [ ] T032 Review SC-008 status — principles III, V, VII, VIII are unchanged and IX, X, XI are appended after VIII (no renumbering) in `.specify/memory/constitution.md`
- [ ] T033 Review NFR-004 status — all principles use `### N. Title` heading format and include `**Rationale**:` block in `.specify/memory/constitution.md`
- [ ] T034 Run markdownlint on `.specify/memory/constitution.md` and fix any formatting regressions

## Dependencies

```text
T001 → T002, T003, T005, T007, T008, T011, T013, T015, T016, T017, T021, T024
T011 → T013 (Principle X inserted after IX)
T013 → T015 (Principle XI inserted after X)
T015 → T016, T017, T021 (references to Principle XI require it to exist)
T002 → T023 (verify Sync Impact Report completeness after all edits)
T003 → T004 (verify FR-002 after implementation)
T005 → T006 (verify FR-003 after implementation)
T007 → T009 (verify FR-004 after implementation)
T008 → T010 (verify FR-011 after implementation)
T015 → T018 (verify FR-008 after implementation)
T016 → T019 (verify FR-009 after implementation)
T017 → T020 (verify FR-010 after implementation)
T011 → T012 (verify FR-006 after implementation)
T013 → T014 (verify FR-007 after implementation)
T021 → T022 (verify FR-005 after implementation)
T003, T005, T007, T008, T015, T016, T017, T011, T013, T021, T024 → T025–T034 (verification after all edits)
```

---
*Generated by Copilot SDK (claude-opus-4.6)*
