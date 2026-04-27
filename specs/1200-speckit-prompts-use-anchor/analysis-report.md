# Cross-Artifact Consistency and Quality Analysis Report

## 1. Findings Table

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| F-01 | D. Constitution Alignment | MEDIUM | Spec §Non-Goals; Constitution §IV | Spec explicitly states "Tests: Not requested" and tasks omit all test tasks. Constitution §IV mandates TDD for all features. The spec's rationale (prompt-wording-only change) is reasonable but lacks an explicit justification as required by the constitution ("Any exception to coverage requires explicit justification in the PR"). | Add a sentence to the spec's Non-Goals or a Note in the tasks file explicitly justifying the TDD exemption per Constitution §IV, e.g., "No runtime code is added or changed; the TDD exemption is justified because the deliverables are prompt templates with no executable logic." |
| F-02 | C. Underspecification | MEDIUM | Spec §NFR-001; Plan §Technical Context; Tasks T012/T013 | NFR-001 states baseline ~1,601 tokens and ceiling ~1,841 tokens without specifying which file(s) the ceiling applies to. The plan clarifies the agent file baseline is 1,508 and template is 2,380, but the tasks split this into two separate validation targets (T012: agent ≤ ~1,750; T013: template "modest and proportional"). T013's ceiling is unmeasured — "modest and proportional" is not a testable threshold. | Define an explicit numeric ceiling for the template file in T013 (e.g., ≤ 2,620 tokens — a ~10% growth allowance consistent with the agent file's ~16% allowance), or update NFR-001 to specify per-file budgets. |
| F-03 | B. Ambiguity | MEDIUM | Tasks T013 | T013 says "growth remaining modest and proportional rather than using the agent-file ceiling." The terms "modest" and "proportional" lack measurable criteria. | Replace with a numeric token ceiling or a percentage growth cap (e.g., "≤ 15% growth from baseline"). |
| F-04 | A. Duplication | LOW | Tasks T009/T010 vs T017 | T009 and T010 (Phase 5) sweep both files for legacy terminology. T017 (Phase 7) performs the same grep plus an additional line-number sweep. The terminology portion is fully duplicated. | Merge the terminology sweep into T017 only, or have T009/T010 focus solely on replacing legacy terms while T017 confirms zero residual matches post-all-phases. Clarify that T017 is a verification pass, not an implementation pass. |
| F-05 | A. Duplication | LOW | Tasks T005 vs T011 | T005 (Phase 2) reads the implement agent and confirms no line-number dependency. T011 (Phase 6) "documents the conclusion from T005." T011 has no independent deliverable beyond restating T005's output. | Fold T011 into T005 by requiring T005 to produce the documented conclusion directly. Remove T011 or convert it to a checkpoint annotation within T005. |
| F-06 | F. Inconsistency | MEDIUM | Spec §NFR-001 vs Plan §Technical Context | Spec says baseline is "approximately 1,601 tokens." Plan measures the agent file at 1,508 tokens and the template at 2,380 tokens. Neither matches 1,601. The spec's number appears to be an estimate that was never reconciled with actual measurement. | Update NFR-001 to reference the measured baselines from the plan (agent: 1,508; template: 2,380) or clarify that 1,601 was an early estimate now superseded by the plan's measurements. |
| F-07 | F. Inconsistency | LOW | Plan §Phase 1 T002 vs Tasks §Phase 1 T002/T003 | Plan has a single task T002 measuring both files. Tasks split this into T002 (agent) and T003 (template), shifting all subsequent task IDs by one. This causes ID drift between plan and tasks (plan's T003 = tasks' T004, etc.). | Acknowledge the ID remapping is intentional or align the plan's task IDs with the tasks file for cross-reference clarity. |
| F-08 | C. Underspecification | LOW | Tasks T004 | T004 says "Audit 3+ existing `tasks.md` files under `specs/`" but does not specify what constitutes a "pass" — how many line-number references must be found to confirm the problem scope? | Add a success criterion, e.g., "Identify at least 1 instance of hardcoded line-number reference to confirm the problem exists, or document that no instances were found and reassess scope." |
| F-09 | C. Underspecification | LOW | Tasks T016 | T016 says "Review 3 representative task-generation scenarios" but these are hypothetical — the task doesn't specify whether to actually run `speckit.tasks` or only inspect prompt text. | Clarify whether T016 requires running `speckit.tasks` against real specs and reviewing output, or is a manual prompt-text review exercise. |
| F-10 | E. Coverage Gap | LOW | Spec §Edge Cases (stale anchor, deleted file) | Edge cases for stale/deleted anchors and ambiguous anchors in minified files are defined in the spec but have no corresponding validation task. T016's "3 representative scenarios" don't explicitly cover these edge cases. | Add edge-case scenarios to T016's validation list, or create a T016b that specifically validates the prompt handles the stale-anchor and ambiguous-anchor edge cases. |
| F-11 | F. Inconsistency | LOW | Spec §Scope Boundary vs Tasks §Notes | Spec says "2 files" and tasks Notes section agrees. However, Tasks T001 installs tiktoken (`pip install tiktoken`), which is a runtime environment change not reflected in the spec's scope boundary. | Acknowledge in the spec or tasks that tiktoken installation is a transient tooling dependency for validation, not a project dependency, to avoid confusion about scope. |
| F-12 | B. Ambiguity | LOW | Spec §Success Criteria SC-001 | SC-001 requires "manual review of at least 3 generated `tasks.md` files across different spec types" but does not define what constitutes "different spec types." | Specify categories, e.g., "one code-heavy spec, one documentation/config spec, one mixed spec" or "3 specs from distinct `specs/` subdirectories." |
| F-13 | D. Constitution Alignment | LOW | Constitution §VI; Tasks | Constitution §VI requires "Output MUST be structured, concise, and include next-step guidance." The spec/tasks don't address what the prompt output format looks like to the end user (the generated tasks). This is tangentially relevant since the deliverable is prompt templates that drive output formatting. | No action strictly required — the constitution principle applies to CLI command output, not generated prompt artifacts. Note for reviewers that this principle is not violated since the deliverable is prompt text, not CLI output. |
| F-14 | E. Coverage Gap | LOW | Spec §FR-005 | FR-005 (prefer stable/distinctive anchors over vague references) has no dedicated validation task. T016 partially covers this via scenario review but doesn't explicitly test for vague-reference rejection. | Extend T016 or T017 to include a check that the prompt text contains explicit guidance against vague references like "near the top" or "in the middle." |

## 2. Coverage Summary Table

| Requirement Key | Has Task? | Task IDs | Notes |
|----------------|-----------|----------|-------|
| FR-001 | ✅ | T006 | Semantic anchors instead of line numbers — core of T006 |
| FR-002 | ✅ | T006 | Code-file anchor types listed in T006 description |
| FR-003 | ✅ | T006, T007 | Non-code anchor types in both agent and template |
| FR-004 | ✅ | T006 | Insertion-point guidance ("before/after/inside/under") |
| FR-005 | ⚠️ | T006 (implicit) | Stable/distinctive preference implied but not explicitly validated (see F-14) |
| FR-006 | ✅ | T006, T007, T008 | Clarity preserved via examples and template updates |
| FR-007 | ✅ | T009, T010, T017 | Unified "semantic anchor" terminology sweep |
| FR-008 | ✅ | T006, T007 | Cross-task reference guidance included |
| NFR-001 | ✅ | T001, T002, T003, T012, T013 | Token measurement pre/post; T013 ceiling is vague (see F-02/F-03) |
| NFR-002 | ✅ | All tasks | Scope limited to 2 files throughout |
| NFR-003 | ✅ | T006, T007, T008 | Concise/scannable guidance in deliverables |
| NFR-004 | ✅ | T005, T011 | Backward compatibility via implement-agent validation |
| NFR-005 | ✅ | T006 | Explicit "MUST" language and negative examples |
| US1 | ✅ | T006, T007 | Core planning prompt changes |
| US2 | ✅ | T007, T008 | Template examples for implementers |
| US3 | ✅ | T009, T010, T017 | Terminology normalization |
| US4 | ✅ | T005, T011 | Validation-only — implement agent compatibility |
| SC-001 | ⚠️ | T016 | Manual review specified but scenarios could be more explicit (see F-09) |

## 3. Metrics

| Metric | Value |
|--------|-------|
| Total Requirements (FR + NFR) | 13 |
| Total User Stories | 4 |
| Total Tasks | 17 |
| Requirement → Task Coverage | 92% (12/13 fully covered; FR-005 implicit only) |
| Ambiguity Count | 2 (F-03, F-12) |
| Duplication Count | 2 (F-04, F-05) |
| Inconsistency Count | 3 (F-06, F-07, F-11) |
| Underspecification Count | 3 (F-02, F-08, F-09) |
| Constitution Alignment Issues | 2 (F-01, F-13) |
| Coverage Gap Issues | 2 (F-10, F-14) |
| Critical Issues Count | 0 |
| High Issues Count | 0 |
| Medium Issues Count | 4 |
| Low Issues Count | 10 |
| **Total Findings** | **14** |

---
*Generated by Copilot SDK (claude-opus-4.6)*
