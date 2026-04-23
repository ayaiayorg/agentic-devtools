# Cross-Artifact Consistency & Quality Analysis Report

**Feature**: SpecKit Pipeline CRITICAL Analysis Gate (#1197)
**Artifacts Analyzed**: spec.md, plan.md, tasks.md
**Date**: 2026-04-23

---

## 1. Findings Table

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| F-01 | F. Inconsistency | **HIGH** | Spec §Key Entities (Gate Result) | Gate Result entity says "monolithic JSON (`status`)" but FR-011, plan, tasks, and Change Log all standardized to `gate_result`. Stale text from pre-standardization. | Change "monolithic JSON (`status`)" to "monolithic JSON (`gate_result`)" in Key Entities |
| F-02 | F. Inconsistency | **HIGH** | Spec §SC-004 | SC-004 lists 8 analysis reports and enumerates `specs/005-*` through `specs/1196-*`. Repo actually contains **9** reports — `specs/1215-fix-remove-invalid-yes/analysis-report.md` is missing from the enumeration. Regression test (T063) would miss this file. | Update SC-004 to list all 9 reports; update T063 to iterate dynamically via `find` rather than a hardcoded list |
| F-03 | F. Inconsistency | **MEDIUM** | NFR-002, Plan §T04/T05 | NFR-002 restricts tooling to "bash, grep, sed, awk" but plan T04 uses `jq -c` for compact JSON in `$GITHUB_OUTPUT`. `jq` is available on `ubuntu-latest` but violates the stated constraint. | Either add `jq` to NFR-002's allowed tool list or implement JSON formatting with `printf`/`awk` |
| F-04 | E. Coverage Gap | **MEDIUM** | FR-009, Plan §Phase 5, Tasks | Plan §Phase 5 mentions editing `speckit-issue-trigger.yml` but **no task exists** for wiring `SPECKIT_CRITICAL_GATE_MODE` env var into that workflow. T027 only covers `speckit-phase-progression.yml`. Monolithic CI runs via `speckit-issue-trigger.yml` will always default to `block`, making draft mode unreachable for that path. | Add task to map `vars.SPECKIT_CRITICAL_GATE_MODE` in `speckit-issue-trigger.yml`'s generate step `env:` block |
| F-05 | E. Coverage Gap | **MEDIUM** | NFR-005, Tasks | NFR-005 (idempotency — running gate twice on same report produces same result) has **no verification task** in the task list. | Add a test case in `test_check_analysis_gate.sh` that runs the gate twice on the same fixture and asserts identical `GATE_RESULT_JSON` output and return codes |
| F-06 | C. Underspecification | **MEDIUM** | FR-005, US2 §AC1, Tasks T032–T037 | US2 AC1 requires "instructions for re-triggering" in the failure comment but neither spec nor template task (T032) defines what those instructions should say (e.g., re-add `speckit` label? push a commit?). | Define the canonical re-trigger mechanism text in T032's template content or in US2 acceptance criteria |
| F-07 | E. Coverage Gap | **MEDIUM** | FR-005, Tasks T037 | T037 tests that finding IDs/summaries/recommendations are present in the failure comment but does **not** assert re-trigger instructions are present (required by US2 AC1). | Extend T037 to verify the comment includes re-trigger instructions text |
| F-08 | C. Underspecification | **MEDIUM** | US2 §AC1, T032 | The `{{findings_table}}` variable rendering format (markdown table vs. bullet list vs. code block) is not specified in the spec. Plan T034 says "markdown table with ID, Summary, Recommendation columns" but the spec acceptance criteria are silent on format. | Add format specification to US2 AC1 or to T032's acceptance criteria |
| F-09 | E. Coverage Gap | **MEDIUM** | T035 | T035 is verification-only ("confirm `failure()` condition triggers" for `speckit:failed` label). Repo confirms the existing handler uses `if: failure()` which **does** trigger — but if a future refactor changes this, there is no implementation contingency in the task. | Rephrase T035 as: verify existing handler triggers; if not, implement the missing condition |
| F-10 | F. Inconsistency | **MEDIUM** | Spec FR-009, Plan §Phase 3 T12 | Spec FR-009 names Phase 5 as "analyze" in the phased workflow, but repo confirms case `5)` in `run_single_phase` runs **both** analyze AND markdownlint. The plan correctly says "after analyze + markdownlint" but this contradicts the spec's Phase 5 = "analyze" label. Gate insertion point (between analyze and markdownlint within case `5)` vs. after both) is ambiguous. | Clarify in FR-009 that phased Phase 5 includes both analyze and markdownlint; specify gate runs after analyze but before markdownlint within case `5)` |
| F-11 | C. Underspecification | **LOW** | FR-010, NFR-003 | "clear error message" for missing/empty reports is stated as a requirement but the specific message template (e.g., `## ❌ SpecKit: Analysis report missing at <path>`) is not defined. | Add error message patterns for `report_missing` and `report_parse_error` cases, consistent with NFR-003 banner format |
| F-12 | E. Coverage Gap | **LOW** | FR-012, Tasks | No negative test verifying that Phases 1–4 are unaffected by the gate. T026 emits default `gate_result=pass` for non-analyze phases but no test asserts the gate function is **not** called. | Add test verifying phases 2, 3, 4 emit default outputs without invoking `check_analysis_gate` |
| F-13 | E. Coverage Gap | **LOW** | Edge Cases §6, Tasks | Spec explicitly lists "Draft mode requested, but report missing/empty/malformed → fail closed" as an edge case. No task tests this combination in draft mode specifically (T058/T059 test report_missing/parse_error but may default to block mode). | Add draft-mode variants of T058/T059 asserting return code 20 and exit 1 regardless of mode |
| F-14 | A. Duplication | **LOW** | FR-009, FR-012 | Both requirements address when/where the gate runs: FR-009 says "consistently in both paths," FR-012 says "only after Phase 5, not Phases 1–4." Overlapping scope. | Add cross-reference from FR-012 to FR-009 or merge FR-012 as a sub-clause |
| F-15 | F. Inconsistency | **LOW** | Plan §Phases 1–7, Tasks §Phases 1–9 | Plan uses implementation phases 1–7; task list reorganizes into 9 user-story-aligned phases with different numbering. Cross-referencing requires mental mapping (e.g., Plan Phase 2 → Task Phases 3+5). | Add a phase mapping table at the top of tasks.md |
| F-16 | E. Coverage Gap | **LOW** | FR-013, T046 | T046 outputs `is_draft=true` to `$GITHUB_OUTPUT` when `--draft` is used but no test task verifies this specific step output. | Add test assertion in T052 or a new task for `is_draft` output verification |
| F-17 | C. Underspecification | **LOW** | US3 §AC4 | US3 scenario 4 says "normal (non-draft) PR is created" when mode=draft but zero CRITICALs, but does not specify whether `is_draft=false` should be emitted as a step output. | Add explicit acceptance criterion for `is_draft` output in the zero-CRITICALs pass case |
| F-18 | B. Ambiguity | **LOW** | NFR-004 | "common markdown formatting variations" is illustrated with examples but is not a closed set. New LLM format variants (e.g., `__CRITICAL__`, HTML `<b>`) could bypass the parser. | Note in NFR-004 that the parser's bold/italic stripping makes the list illustrative, not exhaustive; consider adding HTML tag stripping |

---

## 2. Coverage Summary Table

| Requirement Key | Has Task? | Task IDs | Notes |
|----------------|-----------|----------|-------|
| FR-001 | ✅ | T014 | Dynamic column detection well-specified |
| FR-002 | ✅ | T015 | Resolved-finding regex defined in plan |
| FR-003 | ✅ | T024, T039 | Both phased and monolithic paths covered |
| FR-004 | ✅ | T018 | Human-readable banner output |
| FR-005 | ✅ | T032–T037 | Re-trigger instructions not tested (F-07) |
| FR-006 | ✅ | T035 | Verification-only — no implementation contingency (F-09) |
| FR-007 | ✅ | T044, T045, T048, T050 | Draft PR creation wired end-to-end |
| FR-008 | ✅ | T049 | Auto-merge suppression condition |
| FR-009 | ✅ | T023–T025, T038–T041 | Phase 5 description inconsistent with repo (F-10) |
| FR-010 | ✅ | T013 | No draft-mode-specific fail-closed test (F-13) |
| FR-011 | ✅ | T017, T055–T060 | Structured output thoroughly tested |
| FR-012 | ✅ | T026 | No negative test for Phases 1–4 (F-12) |
| FR-013 | ✅ | T044–T046 | `is_draft` output untested (F-16) |
| FR-014 | ✅ | T061, T062 | Prompt contract update with examples |
| NFR-001 | ✅ | T066 | Performance validation against largest fixture |
| NFR-002 | ⚠️ | — | No verification task; `jq` usage conflicts (F-03) |
| NFR-003 | ✅ | T018, T067 | Consistency review task included |
| NFR-004 | ✅ | T008, T015 | Fixture + parser handle formatting variants |
| NFR-005 | ❌ | — | No idempotency test (F-05) |
| SC-001 | ✅ | T028–T030 | Post-deployment metric; gating implemented |
| SC-002 | ✅ | T037 | Re-trigger instructions gap (F-07) |
| SC-003 | ✅ | T066 | <5s performance check |
| SC-004 | ⚠️ | T063 | Report count wrong: 9 not 8 (F-02) |
| SC-005 | ✅ | T031, T042–T043 | Both paths tested with synthetics |

---

## 3. Metrics

| Metric | Value |
|--------|-------|
| Total Requirements (FR + NFR) | 19 |
| Total Success Criteria | 5 |
| Total Tasks | 70 |
| Requirement → Task Coverage | **89.5%** (17/19 have tasks) |
| Requirements with No Task | 2 (NFR-002, NFR-005) |
| Tasks with No Requirement Mapping | 0 (all map to requirements or legitimate test/infra support) |
| Ambiguity Count | 1 |
| Duplication Count | 1 |
| Underspecification Count | 4 |
| Inconsistency Count | 5 |
| Coverage Gap Count | 7 |
| **Critical Issues** | **0** |
| **High Issues** | **2** (F-01, F-02) |
| **Medium Issues** | **8** |
| **Low Issues** | **8** |
| **Total Findings** | **18** |

---
*Generated by Copilot SDK (claude-opus-4.6)*
