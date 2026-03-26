# Spec 005 — Resolve Test Suite Warnings: Cross-Artifact Consistency & Quality Analysis

---

## 1. Findings Table

| ID | Pass | Severity | Location(s) | Summary | Recommendation |
|----|------|----------|-------------|---------|----------------|
| F01 | A — Resolved | **INFO** | `specs/005-resolve-test-suite-warnings/spec.md` (file on disk) | The `spec.md` file now contains the full specification document, including FRs, NFRs, ACs, and Edge Cases. The earlier placeholder-only content issue has been addressed. | No action required; keep this row as a historical note and ensure future updates keep the spec, plan, and tasks aligned. |
| F02 | A — Resolved | **INFO** | Plan §3 Phase 3a example vs Spec Clarification #3 | The warning `match` string for the `session.py` autopilot case has been aligned between the spec and the plan, so they now describe the same behavior. | No action required; if the warning text changes in `session.py` in future, update both spec and plan together to preserve consistency. |
| F03 | F — Inconsistency | **HIGH** | Plan §4 Phase labels vs Task list Phase labels | Phase numbering is offset by 1 throughout: the plan has 5 phases; the task list has 6 phases because it splits plan Phase 1 (Audit) into two (Phase 1 = audit baseline, Phase 2 = locate sites). All subsequent phase numbers differ (Plan Phase 2 = Task Phase 3, etc.). | Add a cross-reference table mapping plan phases to task phases, or renumber one artifact to match the other. |
| F04 | A — Duplication | **HIGH** | T004 vs T013 | T004 already instructs: "grep entire test suite for `warnings.catch_warnings` usages; record… whether each use is an assertion or a suppression." T013 repeats the identical assertion-vs-suppression classification scoped to one file already in T004's scope. | Delete the classification step from T013; task T013 to only document conversion targets using T004's output as input. Mark T013 as depending on T004. |
| F05 | E — Coverage Gap | **HIGH** | Spec §Edge Cases (5 items) → Task list | None of the 5 spec Edge Cases are referenced or mapped to any task. Scenarios such as `filter="data"` rejecting a valid binary member, or `ResourceWarning` from unclosed handles, have no dedicated test or verification step. | Add edge-case coverage notes to existing tasks (T007, T025) or introduce explicit tasks per edge case; at minimum annotate T001 to specifically surface each EC during audit. |
| F06 | E — Coverage Gap | **HIGH** | Spec §NFRs (6 items) → Task list | 6 NFRs are cited but only 2 are explicitly addressed by tasks (T026 = 100% coverage, T027 = CI pass). The remaining 4 NFRs (e.g., zero DeprecationWarning on Python 3.12+, zero escaped UserWarning in non-intentional tests, pytest exit code 0) have no dedicated task referencing them by NFR ID. | Annotate T012, T018, T022, T023 with their corresponding NFR IDs so traceability is explicit; verify all 6 NFRs map to at least one task. |
| F07 | A — Resolved | **INFO** | T013 dependency on T004 | T013 previously carried a `[P]` (parallel) tag even though its body depended on "each `warnings.catch_warnings` site… **identified in T004**," creating a hard sequential dependency. `tasks.md` has since been updated so T013 is no longer tagged `[P]`, making the implicit dependency on T004 consistent with the tagging. | No action required; keep this row as a historical note and ensure any future parallel tagging reflects real task dependencies. |
| F08 | B — Ambiguity | **HIGH** | Plan §3 Phase 3b / T015 | Two equally-valid suppression fix options are given with no selection rule: pass `autopilot=False` OR mock `_get_copilot_binary`. An implementer exercising the wrong option could leave gaps (e.g., mocking the binary when the test actually exercises autopilot logic, or vice versa). | Define a preference rule: "prefer `autopilot=False`; use binary mock only when the test exercises binary-resolution logic independent of autopilot." |
| F09 | A — Resolved | **INFO** | T029 commit message template | T029's commit message template now hard-codes the concrete issue number `[#958](https://github.com/ayaiayorg/agentic-devtools/issues/958)` instead of the `NNN` placeholder, so the terminal task will not produce a placeholder in the final commit. | No action required; keep this row as a historical note and ensure any future spec-specific commit templates use real issue numbers before execution. |
| F10 | A — Resolved | **INFO** | Spec §Known Third-Party Warning Exemptions table / T003 | The spec's Known Third-Party Warning Exemptions table has been populated, including an entry for `urllib3.exceptions.InsecureRequestWarning`, and T003/T019 now operate against this populated table instead of an "empty, to be populated" placeholder. | No action required; keep this row as a historical note and ensure any future changes to exemptions are reflected in both the spec and the associated tasks. |
| F11 | A — Resolved | **INFO** | Spec §User Stories | `spec.md` now includes explicit Acceptance Criteria sections for US1–US3, giving each user story discrete, measurable ACs that align with verification tasks T012, T018, and T023. | No action required; keep this row as a historical note and ensure future changes keep user story ACs in sync with their corresponding verification tasks. |
| F12 | C — Underspecification | **MEDIUM** | T002 / T005 | Neither task specifies where findings should be recorded. T002 says "categorise"; T005 says "record"; neither names an output artifact (file, section, table). The Warning Emission Site inventory mentioned in T005 has no home. | Specify output artifacts: "append to spec §Known Third-Party Warning Exemptions" for T002/T003; "write to `research.md` §Warning Inventory" for T005. |
| F13 | A — Resolved | **INFO** | T003 vs Spec exemptions table | T003 previously presupposed that `urllib3.exceptions.InsecureRequestWarning` would be the only exemption while the spec's table was still marked "empty, to be populated." The spec's exemptions table has since been updated and T003 is now framed to record all confirmed unavoidable third-party warnings (including `urllib3`) based on the Phase 1 audit outcome. | No action required; keep this row as a historical note and ensure future edits avoid baking audit outcomes into task descriptions. |
| F14 | F — Inconsistency | **MEDIUM** | T007/T008 vs T026 | T007 and T008 already create version-branch tests (Python 3.12 and 3.11) covering both sides of the `sys.version_info` guard. T026 says "if coverage drops due to the `sys.version_info >= (3, 12)` branch split, add branch-parametrized tests." T026 implies tests may not exist, contradicting T007/T008. | Clarify T026 to explicitly exclude the tarfile branch (covered by T007/T008); scope T026 to "any other new code path not covered by prior tasks." |
| F15 | B — Ambiguity | **MEDIUM** | `gh_cli_installer.py` | The inline `# noqa: S202` suppression on the `tar.extract()` call in `gh_cli_installer.py` may be misleading if Bandit's S202 rule is not actually enabled via this project's Ruff configuration. Reviewers cannot tell whether the comment documents an active suppression or is just copied from generic guidance. | Check `pyproject.toml` for `"S202"` (or `"S"` via `select`/`extend-select`) in the Ruff configuration. If S202 is enabled, keep the `# noqa: S202` (and optionally add a brief justification comment); if it is not enabled, remove the `# noqa: S202` from `gh_cli_installer.py` to avoid confusion. |
| F16 | A — Resolved | **INFO** | Plan §2 Research Summary | The plan's research section has been updated to inline the key research decisions with a "summarized here" note, removing the external `research.md` reference. Research decisions are now self-contained within the plan. | No action required; keep this row as a historical note confirming that research decisions are now documented inline in the plan. |
| F17 | C — Underspecification | **MEDIUM** | T006 / T010 | T006 asks "confirm whether `sys` is already imported"; T010 says "add `import sys` if not already present." These two tasks overlap conditionally: if T006 finds `sys` is present, T010 is vacuous. The split creates unnecessary overhead and an orphan task if the condition is true. | Merge T006 and T010 into a single task: "Ensure `sys` is imported at module scope in `gh_cli_installer.py`; note the line number of `tar.extract()` for T011." |
| F18 | A — Duplication | **MEDIUM** | T012 vs T022 / T018 vs T023 | T012 verifies copilot tests post-source-fix; T022 re-runs them with `filterwarnings=["error"]` active. Similarly T018 vs T023. The distinction (pre- vs post-global-filter) is valid, but the plan does not state what T022/T023 can catch that T012/T018 cannot, making the re-run appear redundant. | Add to T022 and T023: "verifies no warning escapes the `pytest.warns()` contexts under the global `error` filter — a regression not detectable in T012/T018 which ran without the global filter." |
| F19 | B — Ambiguity | **MEDIUM** | T025 | "if any appear, categorise and apply the appropriate Phase 3/4/5 fix pattern before proceeding" has no stopping criterion. If fixes introduce new warnings, this becomes an unbounded loop with no escalation path. | Define a gate: "if a newly discovered warning requires a new `ignore` entry not already in the spec exemptions table, stop, update the spec, and get review before adding the entry." |
| F20 | A — Resolved | **INFO** | Plan §2 Technical Context "Key source files" | The plan's "Key source files" section has been updated to list only source files, with test files now called out separately under a "Key test files" heading. This resolves the earlier inconsistency. | No action required; keep this row as a historical note confirming that source and test files are now documented under separate headings. |
| F21 | C — Underspecification | **LOW** | Plan §4 Phase 4 note | The exemptions table is described as a "living record" with no stated ownership, update trigger, or governance (who adds entries? what review is required?). | Specify: "the spec §Known Third-Party Warning Exemptions table is the canonical record; any new `ignore` entry must be added there before being committed to `pyproject.toml`." |
| F22 | A — Duplication | **LOW** | Plan §5 Phase 5 success criteria checklist vs Spec §Success Criteria | The plan's Phase 5 contains a 6-item success criteria checklist that mirrors the spec's Success Criteria section nearly verbatim. The plan also duplicates task content of T024–T027. | Replace the checklist with a reference: "See spec §Success Criteria (SC1–SC6); tracked by tasks T024–T027." |
| F23 | B — Ambiguity | **LOW** | Spec Clarification #4 | "Unavoidable third-party warnings" is used as the criterion for `ignore` exemptions but is not defined. Two developers could disagree on whether a warning is "unavoidable." | Add a definition: "Unavoidable = emitted by a third-party library or Python stdlib on a code path that cannot be changed without forking the dependency or abandoning required functionality." |
| F24 | E — Coverage Gap | **LOW** | T016 | T016 is conditionally scoped to "any other test files identified in T004" with no fallback if T004 finds zero additional files. The task becomes silently vacuous with no explicit completion note. | Add: "If T004 identifies no additional files, mark T016 complete with note: 'No additional files found; T004 output confirms scope is limited to `test_start_copilot_session.py`.'" |
| F25 | C — Underspecification | **LOW** | T029 | T029 instructs to commit "tarfile fix, pytest.warns conversions, autopilot=False updates, and filterwarnings config in the body" but does not specify body formatting (bullet points vs prose) or explicitly tie the example to the rules defined in `COMMIT_CONVENTION.md`. | Specify body format (e.g., "use bullet points per `COMMIT_CONVENTION.md`"); state that the commit message must follow `COMMIT_CONVENTION.md` exactly, and avoid introducing additional mandatory trailers (such as `Co-authored-by`) unless they are first added to that convention document. |

---

## 2. Coverage Summary Table

| Requirement Key | Has Task? | Task IDs | Notes |
|----------------|-----------|----------|-------|
| US1 — Fix `tarfile.extract()` DeprecationWarning at source | ✅ Yes | T007, T008, T009, T010, T011, T012 | Fully covered; T006/T010 merge recommended (F17) |
| US2 — Fix autopilot warning test patterns | ✅ Yes | T013, T014, T015, T016, T017, T018 | Covered; T013 has parallel-tag/dependency conflict (F07); T013/T004 duplication (F04) |
| US3 — Configure global `filterwarnings = ["error"]` | ✅ Yes | T019, T020, T021, T022, T023 | Covered; blocked on T003 completing first (F10) |
| FR1–FR6 | ✅ Yes | T007–T023 | All FRs are defined in spec.md §5 and covered by US task coverage (F01 resolved) |
| NFR: `pytest` exits 0 with `filterwarnings=["error"]` active | ✅ Yes | T024, T025 | |
| NFR: No `DeprecationWarning` from `tarfile` on Python 3.12+ | ✅ Yes | T012, T023 | NFR ID not annotated on tasks (F06) |
| NFR: No `UserWarning` from autopilot in non-intentional tests | ✅ Yes | T018, T022 | NFR ID not annotated on tasks (F06) |
| NFR: Intentional-warning tests use `pytest.warns()` | ✅ Yes | T014 | NFR ID not annotated (F06) |
| NFR: 100% coverage maintained | ⚠️ Conditional | T026 | Task is conditional ("if coverage drops"); should be unconditional verification |
| NFR: `run-pr-checks.sh` exits 0 | ✅ Yes | T027 | |
| EC1–EC5 (5 Edge Cases) | ❌ No | — | Zero task coverage for any edge case (F05) |
| Known Third-Party Warning Exemptions table (spec §) | ⚠️ Partial | T003 | Table currently lists `urllib3.exceptions.InsecureRequestWarning`; T003 must ensure all required exemptions are documented before T019; no blocker enforced (F10) |
| Warning Audit Baseline (Phase 1 deliverable) | ✅ Yes | T001, T002, T003 | Output artifact destination unspecified (F12) |
| Warning Emission Site inventory | ⚠️ Partial | T005 | No output artifact location specified (F12) |
| `research.md` referenced by plan | ✅ Resolved | — | Plan now inlines research decisions; no external `research.md` reference (F16 resolved) |
| `# noqa: S202` annotation correctness | ❌ No | — | No task verifies the bandit rule is enabled before annotating (F15) |

---

## 3. Metrics

| Metric | Value |
|--------|-------|
| Total Named Requirements | 20 (3 US + 6 FR inferred + 6 NFR + 5 EC) |
| Total Tasks | 29 (T001–T029) |
| Requirements with ≥1 task | 15 / 20 |
| **Coverage %** | **75%** |
| Ambiguity Count (Pass B findings) | 4 (F08, F15, F19, F23; match-string drift resolved) |
| Duplication Count (Pass A findings) | 3 (F04, F18, F22) |
| Underspecification Count (Pass C) | 5 (F12, F17, F21, F24, F25) |
| Constitution Issues (Pass D) | 0 (F11 resolved — ACs now present in spec) |
| Coverage Gaps (Pass E) | 4 (F05, F06, F24 + NFR annotation gap) |
| Inconsistency Count (Pass F) | 2 (F03, F14; F07 and F13 resolved) |
| **Critical Issues** | **0** (F01 resolved — spec file now contains the full document) |
| HIGH Severity Issues | 5 (F03–F06, F08; F07, F09, F10 resolved) |
| MEDIUM Severity Issues | 6 (F12, F14, F15, F17–F19; F13 resolved) |
| LOW Severity Issues | 5 (F21–F25) |
| **Total Findings** | **25** |

---
*Generated by Copilot SDK (gpt-5)*
