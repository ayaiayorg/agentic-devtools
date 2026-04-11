# Cross-Artifact Consistency & Quality Analysis

## Spec 1191 — SpecKit Pipeline Markdownlint Validation

---

## 1. Findings Table

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| F01 | **D. Constitution** | **~~CRITICAL~~** RESOLVED | `spec.md` | spec.md now contains full specification body with individually-identifiable, numbered FR/NFR/EC sections and acceptance criteria. | No action needed — finding resolved. |
| F02 | **D. Constitution** | **~~CRITICAL~~** RESOLVED | `checklists/requirements.md` | Checklist file now contains actual checklist items mapping to spec requirements across 3 categories. | No action needed — finding resolved. |
| F03 | **E. Coverage** | **~~HIGH~~** RESOLVED | spec (SC-1), tasks.md | T028 now defines a measurement task for the ≥90% first-push pass rate metric, recording sample size, pass/fail counts, and computed rate from pipeline run history. | No action needed — finding resolved. |
| F04 | **F. Inconsistency** | **~~HIGH~~** RESOLVED | plan.md §4, tasks.md | Terminology has been disambiguated: `plan.md` now uses "Implementation Stages" and `tasks.md` uses "Task Group", avoiding overload with the runtime "Pipeline Phase 7" step. | No action needed — finding resolved. |
| F05 | **C. Underspecification** | **~~HIGH~~** RESOLVED | spec (NFR), tasks T011 | Token estimation is now specified in `spec.md` NFR-004 using a character-count heuristic (`ceil(chars / 4)`), with a 32,000-character max per file to stay under the 8K token target. | No action needed — finding resolved. |
| F06 | **B. Ambiguity** | **~~MEDIUM~~** RESOLVED | plan.md §2.1 | The "~80%" claim has been replaced with qualitative wording ("many common violations"), removing the unverifiable percentage. | No action needed — finding resolved. |
| F07 | **F. Inconsistency** | **~~MEDIUM~~** RESOLVED | plan.md §4.1, tasks T003 | T003 now preserves the full violation shape described in `plan.md`, including `filename`, `line`, `col`, `rule`, and `description` fields. | No action needed — finding resolved. |
| F08 | **F. Inconsistency** | **~~MEDIUM~~** RESOLVED | plan.md §6, tasks.md | plan.md now clarifies that `call_llm` includes retry logic via `call_with_retry` internally, and callers should use `call_llm` directly. The dependency listing is consistent with task usage. | No action needed — finding resolved. |
| F09 | **E. Coverage** | **~~MEDIUM~~** RESOLVED | spec (EC), tasks.md | Spec now contains all 9 edge cases (EC1–EC9) with explicit descriptions and traceable task coverage. | No action needed — finding resolved. |
| F10 | **C. Underspecification** | **~~MEDIUM~~** RESOLVED | tasks T006, T010 | T006 and T010 now specify a concrete test script location (`.github/scripts/speckit-trigger/test_markdownlint_validation.sh`) with clear acceptance criteria and execution context. | No action needed — finding resolved. |
| F11 | **C. Underspecification** | **~~MEDIUM~~** RESOLVED | spec, plan, tasks | EC9 now addresses the empty `$SPEC_DIR` scenario, and T031 implements the guard. | No action needed — finding resolved. |
| F12 | **A. Duplication** | **LOW** | plan.md §3 table, spec (NFR summary) | Plan's "Key Design Constraints" table is a near-verbatim repeat of the spec's NFR metrics (≤120s, ≤600s, <8K, $SPEC_DIR scope, graceful failure). | Acceptable cross-referencing, but plan should cite spec NFRs by ID rather than duplicating prose. |
| F13 | **A. Duplication** | **LOW** | plan.md §2 | Plan §2 “Research Summary” restates key decisions that could be summarized more concisely. | Plan §2 should use a one-liner per decision rather than restating full rationale. |
| F14 | **F. Inconsistency** | **LOW** | plan.md §4 Phase 3.3, tasks T023 | Plan says "Update phase numbering in echo statements (existing are 1-6, new is 7)." T023 says "from `Phase N/6` to `Phase N/7`." Both assume exactly 6 pre-existing phases; if any phases were added in parallel work, the hardcoded counts would be wrong. | Reference the actual current phase count dynamically, or verify the assumption as a prerequisite in T023. |
| F15 | **B. Ambiguity** | **~~LOW~~** RESOLVED | tasks T001 | T001 now specifies a concrete deliverable: document integration assumptions (insertion points, helpers to reuse, config constraints) as inline comments or PR description note. | No action needed — finding resolved. |

---

## 2. Coverage Summary Table

| Requirement Key | Has Task? | Task IDs | Notes |
|----------------|-----------|----------|-------|
| **US1** — Auto-fix resolution (P1) | ✅ | T006, T007, T008, T009 | Well-covered with test + implementation + verification |
| **US2** — LLM semantic remediation (P1) | ✅ | T010, T011, T012, T013, T014, T015 | Well-covered; 6 tasks across prompt, loop, failure, stall |
| **US3** — Graceful failure (P2) | ✅ | T016, T017, T018 | Covered: max-iteration + npx guard + verification |
| **US4** — Iteration logging (P3) | ✅ | T019, T020, T021 | Covered: per-iteration + summary + verification |
| FR: Loop mechanics | ✅ | T007, T008 | Auto-fix + check passes |
| FR: Auto-fix first strategy | ✅ | T007, T009 | Implementation + zero-LLM verification |
| FR: LLM remediation prompts | ✅ | T011 | Prompt construction |
| FR: Footer handling | ✅ | T011, T012 | Strip + re-append |
| FR: Configurable max iterations | ✅ | T002 | Env var with default |
| FR: Stall detection | ✅ | T004, T014 | Fingerprint + comparison |
| NFR: ≤120s common case | ✅ | T028 | Timing verification task |
| NFR: ≤600s worst case | ✅ | T028 | Timing verification task |
| NFR: `$SPEC_DIR`-only scope | ✅ | T025 | Scoping verification task |
| NFR: <8K token prompts | ✅ | T011 | Token counting specified via NFR-004 (F05 resolved) |
| NFR: Reuse existing infra | ✅ | — | Implicit; all tasks use existing helpers |
| NFR: Single-file architecture | ✅ | — | Implicit; all code goes in `generate-spec-from-issue.sh` |
| SC: ≥90% first-push pass rate | ✅ | T028 | Measurement task added (F03 resolved) |
| SC: ≤120s overhead | ✅ | T028 | Covered by timing task |
| SC: Zero unnecessary LLM calls | ✅ | T009 | Auto-fix-only path verification |
| SC: Per-iteration logging | ✅ | T019, T020, T021 | Full coverage |
| SC: No file leakage | ✅ | T025 | Scoping verification |
| EC: Auto-fix-only path | ✅ | T009 | Verified |
| EC: LLM introducing new violations | ✅ | T014 | Stall detection covers this |
| EC: Stall detection | ✅ | T014 | Fingerprint comparison |
| EC: npx unavailability | ✅ | T005, T017 | Guard + integration test |
| EC: 9 edge cases (EC1–EC9) | ✅ | T005, T009, T014, T017, T031 | All 9 edge cases enumerated and covered |
| EC: Empty `$SPEC_DIR` | ✅ | T031 | EC9 + T031 added — finding F11 resolved |

---

## 3. Metrics

| Metric | Value |
|--------|-------|
| **Total Identifiable Requirements** | 26 (4 US + 6 FR topics + 6 NFR + 5 SC + 5 named EC) |
| **Total Tasks** | 31 |
| **Coverage %** | 100% (26/26 with traceable task; 6 resolved structural issues, 0 gaps) |
| **Ambiguity Count** | 0 (F06, F15 resolved) |
| **Duplication Count** | 2 (F12, F13) |
| **Critical Issues Count** | 0 (F01–F11, F15 resolved) |

**Overall Assessment**: The plan and tasks are well-structured with clear dependency chains and good user-story traceability.
The previously blocking structural issues (F01–F11, F15) have been resolved.
The remaining findings (F12–F14) are low-severity duplication and minor inconsistencies.

---
*Generated by Copilot SDK (claude-opus-4.6)*
