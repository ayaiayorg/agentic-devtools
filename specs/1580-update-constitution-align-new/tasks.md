# Tasks: Update Constitution to v1.2.0

## Phase 1: Setup

- [ ] T001 Read current constitution structure and identify exact line ranges for each edit target in `.specify/memory/constitution.md`

## Phase 2: Foundational — Sync Impact Report

- [ ] T002 (FR-012) Replace Sync Impact Report HTML comment block (lines 1–20) with v1.1.0 → v1.2.0 change report listing modified principles (I, II, IV, VI), added principles (IX, X, XI), removed
  content, and templates requiring review in `.specify/memory/constitution.md`

## Phase 3: User Story 4 — Scoped Tool Availability (P1)

- [ ] T003 [US4] (FR-002) Rewrite Principle I: replace "Auto-Approval Friendly Design" (lines 26–35) with "Scoped Tool Availability" describing explicit capability declarations per workflow step,
  acknowledging auto-approval as a transitional mechanism in `.specify/memory/constitution.md`

## Phase 4: User Story 1 — State Architecture (P1)

- [ ] T004 [US1] (FR-003) Rewrite Principle II: replace "Single Source of Truth" (lines 37–46) with "Dual-Layer State Architecture" describing CLI parallel-safe JSON segments + LangGraph
  checkpointing, removing "No distributed configuration" in `.specify/memory/constitution.md`

## Phase 5: User Story 2 — Coverage 100% (P1)

- [ ] T005 [US2] (FR-004) Update Principle IV (line 64): change "Minimum 95% code coverage" to "100% code coverage" referencing ADR-011 in `.specify/memory/constitution.md`
- [ ] T006 [US2] (FR-011) Update Quality Gates → Pre-Commit (line 150): change "Code coverage ≥ 95% for changed files" to "Code coverage = 100% for changed files (per Principle IV and ADR-011)" in
  `.specify/memory/constitution.md`

## Phase 6: User Story 3 — Pre-1.0 Flexibility (P1)

- [ ] T007 [US3] (FR-008) Add new Principle XI "Pre-1.0 Flexibility" after Principle X codifying that breaking changes are allowed pre-1.0, no migration plans required, active removal of dead code in
  `.specify/memory/constitution.md`
- [ ] T008 [US3] (FR-009) Update Development Workflow → Code Changes (line 121): replace backward-compatibility requirement with "Breaking changes are permitted per Principle XI (Pre-1.0 Flexibility)"
  in `.specify/memory/constitution.md`
- [ ] T009 [US3] (FR-010) Update Governance → Amendments (line 193): remove "Migration plan for affected code" item and renumber remaining items in `.specify/memory/constitution.md`

## Phase 7: User Story 5 — Graph-Based Orchestration (P2)

- [ ] T010 [US5] (FR-006) Add new Principle IX "Graph-Based Workflow Orchestration" after Principle VIII describing graph-based orchestration with LangGraph as current implementation, checkpoint state
  recovery, and human-in-the-loop interrupts in `.specify/memory/constitution.md`

## Phase 8: User Story 6 — Dual-Engine Compatibility (P2)

- [ ] T011 [US6] (FR-007) Add new Principle X "Dual-Engine Compatibility" after Principle IX describing opt-in routing (`--engine` flag) and fault isolation between engines in
  `.specify/memory/constitution.md`

## Phase 9: User Story 8 — UX Consistency Update (P3)

- [ ] T012 [US8] (FR-005) Update Principle VI (line 90): remove "Breaking changes to CLI UX require a major version bump and migration notes" and replace with reference to Principle XI in
  `.specify/memory/constitution.md`

## Phase 10: User Story 7 — Sync Impact Report (P2)

- [ ] T013 [US7] (FR-012) Verify the Sync Impact Report (from T002) lists all modified principles (I, II, IV, VI), added principles (IX, X, XI), removed content, and templates requiring review —
  adjust if needed in `.specify/memory/constitution.md`

## Phase 11: Version Footer

- [ ] T014 (FR-001) Update version footer (line 204): change to `**Version**: 1.2.0 | **Ratified**: 2026-05-26 | **Last Amended**: 2026-05-26` in `.specify/memory/constitution.md`

## Final Phase: Verification & Cross-Cutting

- [ ] T015 Run SC-001 verification: confirm `**Version**: 1.2.0` exists in `.specify/memory/constitution.md`
- [ ] T016 Run SC-002 verification: confirm zero occurrences of "95%" in `.specify/memory/constitution.md`
- [ ] T017 Run SC-003 verification: confirm "No distributed configuration" does not appear in `.specify/memory/constitution.md`
- [ ] T018 Run SC-004 verification: confirm "Breaking changes to CLI UX require a major version bump" does not appear in `.specify/memory/constitution.md`
- [ ] T019 Run SC-005 verification: confirm "Migration plan for affected code" does not appear in `.specify/memory/constitution.md`
- [ ] T020 Run SC-006 verification: confirm Principles IX, X, XI exist with correct titles in `.specify/memory/constitution.md`
- [ ] T021 Run SC-007 verification: confirm Sync Impact Report references `1.1.0 → 1.2.0` in `.specify/memory/constitution.md`
- [ ] T022 Run SC-008 verification: confirm principles III, V, VII, VIII are unchanged and IX, X, XI are appended after VIII (no renumbering) in `.specify/memory/constitution.md`
- [ ] T023 Run NFR-004 verification: confirm all principles use `### N. Title` heading format and include `**Rationale**:` block in `.specify/memory/constitution.md`
- [ ] T024 Run markdownlint on `.specify/memory/constitution.md` to verify no formatting regressions

## Dependencies

```text
T001 → T002, T003, T004, T005, T006, T007, T008, T009, T010, T011, T012, T014
T010 → T011 (Principle X inserted after IX)
T011 → T007 (Principle XI inserted after X)
T007 → T008, T009, T012 (references to Principle XI require it to exist)
T002 → T013 (verify Sync Impact Report completeness after all edits)
T003, T004, T005, T006, T007, T008, T009, T010, T011, T012, T014 → T015–T024 (verification after all edits)
```

---
*Generated by Copilot SDK (claude-opus-4.6)*
