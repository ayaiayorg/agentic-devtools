# Analysis Report: SpecKit Pipeline Task Deduplication (#1201)

## Findings Table

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| F-01 | B. Ambiguity | MEDIUM | Spec NFR-002 | "SHOULD be deterministic" is vague — no criteria for what constitutes acceptable variance or how to verify determinism | Define what "deterministic" means operationally (e.g., same findings IDs, same severity, same cluster membership) and under what conditions variance is tolerated (e.g., rationale wording) |
| F-02 | B. Ambiguity | LOW | Spec NFR-001 | Double negative: "No single finding's rationale text MUST NOT exceed 500 characters" — grammatically means rationale must always exceed 500 chars | Rewrite as "No single finding's rationale text SHALL exceed 500 characters" or "Each finding's rationale MUST be at most 500 characters" |
| F-03 | F. Inconsistency | MEDIUM | Spec FR-002, Plan §3 | FR-002 states "Phase 3 (plan) MUST define numeric thresholds or heuristics for each dimension before implementation begins" but Plan §3 AD-3 only provides qualitative-to-numeric mappings for file path (≥50%) — description similarity and code section overlap lack numeric thresholds | Plan should define explicit heuristics for description similarity (e.g., "substantially same intent" operationalized as a decision criterion) and code section overlap (e.g., exact name match vs. partial) with enough specificity for the LLM prompt |
| F-04 | F. Inconsistency | MEDIUM | Spec FR-006, Tasks T022/T028 | FR-006 says findings MUST be "JSON-serializable objects" (mandatory), but Plan AD-2 and Task T028 treat the JSON block as optional (Phase 3 is skippable). The table format satisfies FR-006's field requirements but not the "JSON-serializable object" representation | Clarify whether FR-006 is satisfied by the table alone (fields present in columns) or requires actual JSON output. If table suffices, soften FR-006 wording; if JSON is required, T028 should not be optional |
| F-05 | A. Duplication | LOW | Plan Phase 1 Task 8, Tasks T006 | Plan Phase 1 Task 8 ("Align finding ID examples...from category-initial format to F-NN") and T006 describe the same work with identical scope | Consolidate — T006 already covers this; remove the duplicate reference in the plan or cross-reference explicitly |
| F-06 | E. Coverage Gap | MEDIUM | Spec NFR-002 | NFR-002 (deterministic behavior) has no corresponding task for validation — no task verifies that two runs on the same input produce consistent results | Add a validation task: run analysis twice on the same synthetic spec and compare Category G findings for consistency |
| F-07 | E. Coverage Gap | LOW | Spec NFR-004 | NFR-004 (future extensibility) has no explicit task coverage, though it is implicitly satisfied by T028/T029 (structured output + read-only constraint) | Add a note in T028 or T029 explicitly mapping to NFR-004 for traceability |
| F-08 | F. Inconsistency | MEDIUM | Plan §4 Phase 3 vs Tasks Phase 6 | Plan Phase 3 is titled "Structured Output Contract (Optional)" and contains 4 tasks; Tasks Phase 6 (US4) maps this to T028–T031 but bundles FR-005 read-only reminders (T029) which are not optional — FR-005 is mandatory | Split T029 (read-only constraint) out of the optional US4 phase into an earlier mandatory phase, or mark only T028/T031 as optional while keeping T029 mandatory |
| F-09 | F. Inconsistency | MEDIUM | Spec Edge Cases | Edge case "contradictory verbs or expected outcomes" should be `conflicting` — but no acceptance scenario explicitly tests contradictory verbs as distinct from general conflicting tasks | Add an acceptance scenario or validation task specifically targeting contradictory verb detection (e.g., "delete file X" vs. "update file X") |
| F-10 | F. Inconsistency | LOW | Tasks T013 | T013 references both `/speckit.analyze` in Copilot Chat and `agdt-speckit-analyze` in the terminal. The CLI command is real, but the surrounding plan/instructions may not document clearly when to use the chat command versus the CLI entry point | Rephrase T013 and any supporting documentation to clarify that both invocation paths are valid, and document the intended usage/context for each to avoid confusion |
| F-11 | D. Constitution Alignment | LOW | Tasks, `.specify/memory/constitution.md` | The repo has a Speckit constitution at `.specify/memory/constitution.md` and the analyze agent template references it, but no task includes an explicit quality-gate step confirming Category G output aligns with the constitution's principles | Add a constitution-alignment validation step to the analysis tasks (e.g., verify Category G findings reference constitution principles), or add a note in T012/T025 documenting that the existing analyze workflow already enforces alignment via the agent template's constitution injection |
| F-12 | F. Inconsistency | MEDIUM | Spec FR-003, Plan §3 | The boundary between `duplicate` and `overlapping` with ≥2 strong dimensions is underspecified — if two tasks match on all 3 dimensions but have slightly different wording, is that `duplicate` or `overlapping`? | Add a distinguishing criterion: e.g., `duplicate` requires all available dimensions to match AND no scope differentiation, while `overlapping` with ≥2 dimensions implies partial scope distinction |

## Coverage Summary Table

| Requirement Key | Has Task? | Task IDs | Notes |
|----------------|-----------|----------|-------|
| FR-001 | ✅ | T009, T012 | Category G added to both agent prompt and pipeline inline prompt |
| FR-002 | ✅ | T010, T011, T012 | Dimensions defined with qualitative criteria; see F-03 for threshold gap |
| FR-003 | ✅ | T014, T015, T016, T017 | Classification rules and severity mapping covered |
| FR-004 | ✅ | T021, T025 | Grouping rules and validation |
| FR-005 | ✅ | T013, T029, T031 | Read-only constraint; see F-08 for phase placement concern |
| FR-006 | ✅ | T022, T028 | Structured output; see F-04 for mandatory vs optional tension |
| FR-007 | ✅ | T023, T024, T026 | Metrics integration and validation |
| NFR-001 | ✅ | T022 | 500-char constraint and one-finding-per-cluster rule |
| NFR-002 | ⚠️ | — | No dedicated validation task for determinism (F-06) |
| NFR-003 | ✅ | T013 | Backward compatibility validated via non-overlapping task run |
| NFR-004 | ⚠️ | T028, T029 | Extensibility via structured format; no explicit traceability (F-07) |

## Metrics

| Metric | Value |
|--------|-------|
| Total Requirements | 11 (7 FR + 4 NFR) |
| Total Tasks | 36 (T001–T036) |
| Coverage % | 82% explicit (9/11 requirements have dedicated tasks); NFR-002 has partial coverage (no determinism validation task — see F-06); NFR-004 has implicit coverage via T028/T029 (see F-07) |
| Ambiguity Count | 2 (F-01, F-02) |
| Duplication Count | 1 (F-05) |
| Critical Issues Count | 0 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
