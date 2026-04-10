# Cross-Artifact Consistency & Quality Analysis

## Spec 1191 — SpecKit Pipeline Markdownlint Validation

---

## 1. Findings Table

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| F01 | **D. Constitution** | **~~CRITICAL~~** RESOLVED | `spec.md` | spec.md now contains full specification body with individually-identifiable, numbered FR/NFR/EC sections and acceptance criteria. | No action needed — finding resolved. |
| F02 | **D. Constitution** | **~~CRITICAL~~** RESOLVED | `checklists/requirements.md` | Checklist file now contains actual checklist items mapping to spec requirements across 3 categories. | No action needed — finding resolved. |
| F03 | **E. Coverage** | **HIGH** | spec (SC-1), tasks.md | Success criterion "≥90% first-push pass rate" has no corresponding task for measurement or validation. No task defines how this metric is collected, baselined, or verified. | Add a task to define measurement methodology (e.g., track lint-clean rate across N pipeline runs) and a verification step. |
| F04 | **F. Inconsistency** | **HIGH** | plan.md §4, tasks.md | Overloaded "Phase" terminology: plan.md uses "Phase 1–4" for implementation phases while tasks.md uses "Phase 1–8" with different boundaries. Both also reference "Phase 7" as the pipeline step. Three incompatible phase-numbering schemes in one feature. | Disambiguate: use "Pipeline Phase 7" for the runtime step, "Implementation Stage 1–4" in plan.md, and "Task Group 1–8" in tasks.md. |
| F05 | **C. Underspecification** | **HIGH** | spec (NFR), tasks T011 | NFR "<8K token prompts" lacks specification of how tokens are counted. No task defines a token-counting or estimation mechanism. In bash, there is no native tokenizer — the plan and tasks hand-wave this constraint. | Specify the token estimation method (e.g., `wc -c` / 4 heuristic, or explicit truncation at N chars). Add a task for implementation + validation. |
| F06 | **B. Ambiguity** | **MEDIUM** | plan.md §2.1 | "~80% of violations" is an unverifiable claim used to justify the auto-fix-first strategy. No source data or benchmark is cited. | Either cite a measurement (e.g., from research.md on a sample corpus) or remove the percentage and state "most auto-fixable rules" qualitatively. |
| F07 | **F. Inconsistency** | **MEDIUM** | plan.md §4.1, tasks T003 | plan.md specifies violation format as `filename:line:col rule/alias description` (includes column). T003 describes output as `filename:line:rule` tuples — drops column and description fields. | Align T003 to match the full output format from plan.md, or explicitly document which fields are discarded and why. |
| F08 | **F. Inconsistency** | **MEDIUM** | plan.md §6, tasks.md | plan.md lists `call_with_retry` as an internal dependency. No task references it; all tasks use `call_llm`. Whether retry logic is expected (via `call_with_retry` wrapping `call_llm`, or built into `call_llm` itself) is unclear. | Clarify the call chain in plan.md. If `call_llm` already includes retry logic, remove `call_with_retry` from the dependency list. If retry is separate, add a task to wire it in. |
| F09 | **E. Coverage** | **~~MEDIUM~~** RESOLVED | spec (EC), tasks.md | Spec now contains all 8 edge cases (EC1–EC8) with explicit descriptions and traceable task coverage. | No action needed — finding resolved. |
| F10 | **C. Underspecification** | **MEDIUM** | tasks T006, T010 | Both test tasks say "manual test script or inline validation" without defining where test artifacts live, how they're triggered in CI, or whether they persist. Testing strategy is vague. | Specify test artifact location (e.g., a `test_markdownlint_validation.sh` script) and whether these are one-off manual checks or repeatable CI steps. |
| F11 | **C. Underspecification** | **~~MEDIUM~~** RESOLVED | spec, plan, tasks | EC9 now addresses the empty `$SPEC_DIR` scenario, and T030 implements the guard. | No action needed — finding resolved. |
| F12 | **A. Duplication** | **LOW** | plan.md §3 table, spec (NFR summary) | Plan's "Key Design Constraints" table is a near-verbatim repeat of the spec's NFR metrics (≤120s, ≤600s, <8K, $SPEC_DIR scope, graceful failure). | Acceptable cross-referencing, but plan should cite spec NFRs by ID rather than duplicating prose. |
| F13 | **A. Duplication** | **LOW** | plan.md §2 | Plan §2 “Research Summary” restates key decisions that could be summarized more concisely. | Plan §2 should use a one-liner per decision rather than restating full rationale. |
| F14 | **F. Inconsistency** | **LOW** | plan.md §4 Phase 3.3, tasks T023 | Plan says "Update phase numbering in echo statements (existing are 1-6, new is 7)." T023 says "from `Phase N/6` to `Phase N/7`." Both assume exactly 6 pre-existing phases; if any phases were added in parallel work, the hardcoded counts would be wrong. | Reference the actual current phase count dynamically, or verify the assumption as a prerequisite in T023. |
| F15 | **B. Ambiguity** | **LOW** | tasks T001 | "Read and understand" is a non-verifiable task with no deliverable or acceptance criterion. | Reframe as "Document key integration points in the script for Phase 7 insertion" or merge into T002 as a prerequisite note. |

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
| NFR: <8K token prompts | ⚠️ | T011 | Token counting mechanism unspecified (F05) |
| NFR: Reuse existing infra | ✅ | — | Implicit; all tasks use existing helpers |
| NFR: Single-file architecture | ✅ | — | Implicit; all code goes in `generate-spec-from-issue.sh` |
| SC: ≥90% first-push pass rate | ❌ | — | **No task** (F03) |
| SC: ≤120s overhead | ✅ | T028 | Covered by timing task |
| SC: Zero unnecessary LLM calls | ✅ | T009 | Auto-fix-only path verification |
| SC: Per-iteration logging | ✅ | T019, T020, T021 | Full coverage |
| SC: No file leakage | ✅ | T025 | Scoping verification |
| EC: Auto-fix-only path | ✅ | T009 | Verified |
| EC: LLM introducing new violations | ✅ | T014 | Stall detection covers this |
| EC: Stall detection | ✅ | T014 | Fingerprint comparison |
| EC: npx unavailability | ✅ | T005, T017 | Guard + integration test |
| EC: 9 edge cases (EC1–EC9) | ✅ | T005, T009, T014, T017, T030 | All 9 edge cases enumerated and covered |
| EC: Empty `$SPEC_DIR` | ✅ | T030 | EC9 + T030 added — finding F11 resolved |

---

## 3. Metrics

| Metric | Value |
|--------|-------|
| **Total Identifiable Requirements** | 26 (4 US + 6 FR topics + 6 NFR + 5 SC + 5 named EC) |
| **Total Tasks** | 30 |
| **Coverage %** | 96% (25/26 with traceable task; 3 resolved structural issues, 0 gaps) |
| **Ambiguity Count** | 2 (F06, F15) |
| **Duplication Count** | 2 (F12, F13) |
| **Critical Issues Count** | 0 (F01, F02, F11 resolved — spec, checklist, and edge cases now contain full content) |

**Overall Assessment**: The plan and tasks are well-structured with clear dependency chains and good user-story traceability.
The previously blocking structural issues (F01, F02, F11) have been resolved — spec.md and checklists/requirements.md
now contain full content, and EC9 + T030 address the empty spec directory scenario.
The remaining findings are tractable refinements.

---
*Generated by Copilot SDK (claude-opus-4.6)*
