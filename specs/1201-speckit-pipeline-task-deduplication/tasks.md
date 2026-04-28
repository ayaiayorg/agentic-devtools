# Tasks: SpecKit Pipeline Task Deduplication in Analysis Step

**Source Issue**: [#1201](https://github.com/ayaiayorg/agentic-devtools/issues/1201)

## User Story Map

| Label | Summary | Priority |
|-------|---------|----------|
| US1 | Detect duplicate or overlapping tasks during analysis | P1 |
| US2 | Classify overlap severity correctly | P1 |
| US3 | Report grouped findings and useful metrics | P2 |
| US4 | Support future opt-in remediation in task processing | P3 |

---

## Phase 1: Setup

- [ ] T001 Review existing detection passes A–F in `.github/agents/speckit.analyze.agent.md` to identify insertion point and structural conventions
- [ ] T002 [P] Review existing detection passes A–F in `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` (`run_analyze_phase` inline prompt) to identify insertion point and structural
  conventions
- [ ] T003 [P] Review existing analysis reports in `specs/*/analysis-report.md` to confirm findings table format, `F-NN` ID convention, and severity columns
- [ ] T004 [P] Review `.specify/templates/commands/analyze.md` to understand SDK template structure and sync requirements
- [ ] T005 [P] Review `check-analysis-gate.sh` (spec #1197) to confirm Category G findings table compatibility requirements

---

## Phase 2: Foundational

- [ ] T006 Align finding ID examples in `.github/agents/speckit.analyze.agent.md` from category-initial format (`A1`, `B1`) to sequential `F-NN` format used in pipeline/report output
  - Depends on: T001
- [ ] T007 Add explicit scope distinction note between Category A (duplicate *requirements*) and Category G (duplicate *tasks*) in `.github/agents/speckit.analyze.agent.md`
  - Depends on: T006
- [ ] T008 Add same scope distinction note between Category A and Category G in `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` inline prompt
  - Depends on: T002

---

## Phase 3: US1 — Detect Duplicate or Overlapping Tasks (P1)

- [ ] T009 [US1] Add `#### G. Task Deduplication` section header and preamble after `#### F. Inconsistency` in `.github/agents/speckit.analyze.agent.md`, satisfying FR-001 (new Category G added to
  analysis passes alongside A–F)
  - Depends on: T007
- [ ] T010 [US1] Define three comparison dimensions (description similarity, file path overlap, code section overlap) with qualitative criteria and fixed heuristics in the Category G section of
  `.github/agents/speckit.analyze.agent.md`, implementing FR-002
  - Depends on: T009
- [ ] T011 [US1] Add edge case handling instructions to Category G section in `.github/agents/speckit.analyze.agent.md`: missing dimensions, broad-vs-narrow scope, contradictory verbs,
  single-dimension-only evidence
  - Depends on: T010
- [ ] T012 [US1] Add Category G detection pass (section header, dimensions, edge cases) to inline prompt in `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` (`run_analyze_phase`) matching
  agent prompt, satisfying FR-001 for the pipeline path
  - Depends on: T008, T010, T011
- [ ] T013 [US1] [P] Validate: run `/speckit.analyze` in Copilot Chat or `agdt-speckit-analyze` in the terminal on an existing spec with known non-overlapping tasks → verify Category G reports no
  findings and categories A–F are unchanged (FR-005 read-only behavior confirmed)
  - Depends on: T012

---

## Phase 4: US2 — Classify Overlap Severity Correctly (P1)

- [ ] T014 [US2] Define classification rules (duplicate/overlapping/conflicting) with explicit severity mapping in Category G section of `.github/agents/speckit.analyze.agent.md`, implementing FR-003
  - Depends on: T010
- [ ] T015 [US2] Add severity decision tree to Category G section: duplicate→CRITICAL, conflicting→CRITICAL, overlapping ≥2 dimensions→CRITICAL, overlapping 1 dimension→HIGH, per FR-003 graduated
  model
  - Depends on: T014
- [ ] T016 [US2] Extend §5 Severity Assignment in `.github/agents/speckit.analyze.agent.md` with Category G entries: CRITICAL for duplicates/conflicts/multi-dimension overlap, HIGH for
  single-dimension overlap
  - Depends on: T015
- [ ] T017 [US2] Mirror classification rules, severity decision tree, and §5 severity entries to inline prompt in `.github/scripts/speckit-trigger/generate-spec-from-issue.sh`
  - Depends on: T015, T016, T012
- [ ] T018 [US2] Validate: run `agdt-speckit-analyze` on synthetic spec with duplicate tasks → verify `duplicate` / `CRITICAL` finding
  - Depends on: T017
- [ ] T019 [US2] Validate: run `agdt-speckit-analyze` on synthetic spec with single-dimension overlapping tasks → verify `overlapping` / `HIGH` finding
  - Depends on: T017
- [ ] T020 [US2] Validate: run `agdt-speckit-analyze` on synthetic spec with conflicting tasks → verify `conflicting` / `CRITICAL` finding
  - Depends on: T017

---

## Phase 5: US3 — Report Grouped Findings and Useful Metrics (P2)

- [ ] T021 [US3] Add grouping rules (transitive closure, one finding per cluster, highest severity wins) to Category G section in `.github/agents/speckit.analyze.agent.md`, implementing FR-004
  - Depends on: T015
- [ ] T022 [US3] Add 500-character rationale constraint and structured finding output contract (overlap_type, severity, task_ids, dimensions, rationale) to Category G section in
  `.github/agents/speckit.analyze.agent.md`, implementing FR-006 and NFR-001
  - Depends on: T021
- [ ] T023 [US3] Extend §6 Metrics block in `.github/agents/speckit.analyze.agent.md` with Category G metrics: total finding count, counts by overlap type, multi-task group count, implementing FR-007
  - Depends on: T022
- [ ] T024 [US3] Mirror grouping rules, rationale constraint, structured output contract, and metrics to inline prompt in `.github/scripts/speckit-trigger/generate-spec-from-issue.sh`
  - Depends on: T022, T023, T017
- [ ] T025 [US3] Validate: run `agdt-speckit-analyze` on synthetic spec with 3+ task overlap cluster → verify single grouped finding emitted (not pairwise), FR-004 satisfied
  - Depends on: T024
- [ ] T026 [US3] Validate: verify metrics section includes deduplication finding count, counts by overlap type, and multi-task group count in output report
  - Depends on: T025
- [ ] T027 [US3] Validate: verify gate script (`check-analysis-gate.sh`, spec #1197) can parse Category G findings from findings table without modification
  - Depends on: T024

---

## Phase 6: US4 — Support Future Opt-In Remediation (P3)

- [ ] T028 [US4] Add optional `### Category G Structured Findings` JSON block instruction to Category G section in `.github/agents/speckit.analyze.agent.md` with schema (id, overlap_type, severity,
  task_ids, dimensions, rationale) for programmatic consumption
  - Depends on: T022
- [ ] T029 [US4] Add explicit read-only constraint reminder and note reserving opt-in remediation for future `speckit.tasks` to Category G section in `.github/agents/speckit.analyze.agent.md`,
  reinforcing FR-005
  - Depends on: T028
- [ ] T030 [US4] Mirror structured JSON block instruction and read-only constraint to inline prompt in `.github/scripts/speckit-trigger/generate-spec-from-issue.sh`
  - Depends on: T029, T024
- [ ] T031 [US4] Validate: confirm structured JSON block (if emitted) is valid JSON and parseable, and confirm analysis does not mutate tasks (FR-005)
  - Depends on: T030

---

## Phase 7: Polish & Cross-Cutting

- [ ] T032 Mirror all Category G changes to `.specify/templates/commands/analyze.md` SDK template
  - Depends on: T024, T029
- [ ] T033 Verify `.github/prompts/speckit.analyze.prompt.md` correctly delegates to updated agent (no content changes needed if thin wrapper)
  - Depends on: T032
- [ ] T034 Update `SPEC_DRIVEN_DEVELOPMENT.md` if it references analysis categories, adding Category G
  - Depends on: T024
- [ ] T035 Update `docs/copilot-commands.md` if it describes analyze output, adding Category G
  - Depends on: T024
- [ ] T036 End-to-end validation: run full `agdt-speckit-analyze` on a real spec with intentionally duplicated tasks and verify complete report output including findings table, severity, grouping,
  metrics, and optional JSON block
  - Depends on: T032, T033

---
*Generated by Copilot SDK (claude-opus-4.6)*
