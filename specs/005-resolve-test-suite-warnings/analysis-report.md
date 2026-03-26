# Spec 005 — Resolve Test Suite Warnings: Cross-Artifact Consistency & Quality Analysis

---

## 1. Findings Table

| ID | Pass | Severity | Location(s) | Summary | Recommendation |
|----|------|----------|-------------|---------|----------------|
| F01 | D — Constitution | **CRITICAL** | `specs/005-resolve-test-suite-warnings/spec.md` (file on disk) | The spec.md file on disk contains only a generation summary paragraph, not the actual specification document. All section headers (FRs, NFRs, ACs, Edge Cases) referenced in the plan and tasks are unreachable for verification. | Replace file content with the full spec document. All downstream analysis is blocked without the authoritative text. |
| F02 | F — Inconsistency | **HIGH** | Plan §3 Phase 3a example vs Spec Clarification #3 | Warning `match` string is inconsistent: Spec Clarification #3 states `match="--autopilot is not supported"`; Plan Phase 3a code sample uses `match="gh copilot is not available"`. These resolve to different branches of `session.py`. | Verify the exact `warnings.warn()` message in `session.py` and canonicalise one match string across spec, plan, and tasks. |
| F03 | F — Inconsistency | **HIGH** | Plan §4 Phase labels vs Task list Phase labels | Phase numbering is offset by 1 throughout: the plan has 5 phases; the task list has 6 phases because it splits plan Phase 1 (Audit) into two (Phase 1 = audit baseline, Phase 2 = locate sites). All subsequent phase numbers differ (Plan Phase 2 = Task Phase 3, etc.). | Add a cross-reference table mapping plan phases to task phases, or renumber one artifact to match the other. |
| F04 | A — Duplication | **HIGH** | T004 vs T013 | T004 already instructs: "grep entire test suite for `warnings.catch_warnings` usages; record… whether each use is an assertion or a suppression." T013 repeats the identical assertion-vs-suppression classification scoped to one file already in T004's scope. | Delete the classification step from T013; task T013 to only document conversion targets using T004's output as input. Mark T013 as depending on T004. |
| F05 | E — Coverage Gap | **HIGH** | Spec §Edge Cases (5 items) → Task list | None of the 5 spec Edge Cases are referenced or mapped to any task. Scenarios such as `filter="data"` rejecting a valid binary member, or `ResourceWarning` from unclosed handles, have no dedicated test or verification step. | Add edge-case coverage notes to existing tasks (T007, T025) or introduce explicit tasks per edge case; at minimum annotate T001 to specifically surface each EC during audit. |
| F06 | E — Coverage Gap | **HIGH** | Spec §NFRs (6 items) → Task list | 6 NFRs are cited but only 2 are explicitly addressed by tasks (T026 = 100% coverage, T027 = CI pass). The remaining 4 NFRs (e.g., zero DeprecationWarning on Python 3.12+, zero escaped UserWarning in non-intentional tests, pytest exit code 0) have no dedicated task referencing them by NFR ID. | Annotate T012, T018, T022, T023 with their corresponding NFR IDs so traceability is explicit; verify all 6 NFRs map to at least one task. |
| F07 | F — Inconsistency | **HIGH** | T013 `[P]` parallel tag + task body | T013 is tagged `[P]` (can run in parallel) but its body states "for each `warnings.catch_warnings` site… **identified in T004**," creating a hard sequential dependency. T013 cannot begin until T004 is complete. | Remove `[P]` from T013; add explicit dependency notation "depends on T004." |
| F08 | B — Ambiguity | **HIGH** | Plan §3 Phase 3b / T015 | Two equally-valid suppression fix options are given with no selection rule: pass `autopilot=False` OR mock `_get_copilot_binary`. An implementer exercising the wrong option could leave gaps (e.g., mocking the binary when the test actually exercises autopilot logic, or vice versa). | Define a preference rule: "prefer `autopilot=False`; use binary mock only when the test exercises binary-resolution logic independent of autopilot." |
| F09 | B — Ambiguity | **HIGH** | T029 commit message template | Commit message contains `[#NNN](https://github.com/ayaiayorg/agentic-devtools/issues/NNN)` with `NNN` as an unresolved placeholder. This is the terminal task and the placeholder will appear verbatim if not resolved. | Resolve the issue number before implementation begins, or add a sub-step to T029: "look up the GitHub issue number for spec 005 before composing the message." |
| F10 | C — Underspecification | **HIGH** | Spec §Known Third-Party Warning Exemptions table / T003 | The exemptions table is "empty, to be populated" in the spec — a deferred deliverable. T003 must complete before T019 can correctly set `filterwarnings` entries, yet no explicit dependency or blocker relationship is stated between T003 and T019. | Mark T019 as blocked by T003; add an acceptance criterion to T003: "spec exemptions table must be populated and reviewed before Phase 5 tasks proceed." |
| F11 | D — Constitution | **MEDIUM** | Spec §User Stories | The spec summary states "3 User Stories" exist but does not confirm each has discrete, measurable acceptance criteria. Without visible ACs, tasks T012, T018, T023 (the per-US verification steps) cannot be verified against spec criteria. | Confirm and, if missing, add explicit ACs to each user story (e.g., US1 AC: "On Python 3.12+, `filter='data'` kwarg is passed; on Python 3.11, it is omitted"). |
| F12 | C — Underspecification | **MEDIUM** | T002 / T005 | Neither task specifies where findings should be recorded. T002 says "categorise"; T005 says "record"; neither names an output artifact (file, section, table). The Warning Emission Site inventory mentioned in T005 has no home. | Specify output artifacts: "append to spec §Known Third-Party Warning Exemptions" for T002/T003; "write to `research.md` §Warning Inventory" for T005. |
| F13 | F — Inconsistency | **MEDIUM** | T003 vs Spec exemptions table | T003 says "confirm that `urllib3.exceptions.InsecureRequestWarning` is the only entry," presupposing the audit outcome. The spec's exemptions table is explicitly "empty, to be populated," signalling the outcome is unknown. T003 bakes in an answer that Phase 1 is supposed to discover. | Rewrite T003: "Record all confirmed unavoidable third-party warnings. Verify whether `urllib3.exceptions.InsecureRequestWarning` is the only one; if additional warnings are found, add them before proceeding to T019." |
| F14 | F — Inconsistency | **MEDIUM** | T007/T008 vs T026 | T007 and T008 already create version-branch tests (Python 3.12 and 3.11) covering both sides of the `sys.version_info` guard. T026 says "if coverage drops due to the `sys.version_info >= (3, 12)` branch split, add branch-parametrized tests." T026 implies tests may not exist, contradicting T007/T008. | Clarify T026 to explicitly exclude the tarfile branch (covered by T007/T008); scope T026 to "any other new code path not covered by prior tasks." |
| F15 | B — Ambiguity | **MEDIUM** | Plan §4 Phase 2 / T011 code sample | `# noqa: S202` appears in the plan's code sample without confirming whether bandit's S202 rule is enabled in this project's ruff configuration. If S202 is not active, the comment is misleading and may cause confusion in code review. | Grep `pyproject.toml` for `"S"` or `"S202"` in the ruff select list; add the noqa annotation only if the rule is enabled. |
| F16 | E — Coverage Gap | **MEDIUM** | Plan §2 Research Summary | The plan references `research.md` as containing "full decisions" but no task creates, validates, or maintains this file. If it does not exist or becomes stale, the plan's justifications are unverifiable. | Add a task (or note in T001) to verify `research.md` exists and is current; if it is a working document only, remove the plan reference or link to a stable location. |
| F17 | C — Underspecification | **MEDIUM** | T006 / T010 | T006 asks "confirm whether `sys` is already imported"; T010 says "add `import sys` if not already present." These two tasks overlap conditionally: if T006 finds `sys` is present, T010 is vacuous. The split creates unnecessary overhead and an orphan task if the condition is true. | Merge T006 and T010 into a single task: "Ensure `sys` is imported at module scope in `gh_cli_installer.py`; note the line number of `tar.extract()` for T011." |
| F18 | A — Duplication | **MEDIUM** | T012 vs T022 / T018 vs T023 | T012 verifies copilot tests post-source-fix; T022 re-runs them with `filterwarnings=["error"]` active. Similarly T018 vs T023. The distinction (pre- vs post-global-filter) is valid, but the plan does not state what T022/T023 can catch that T012/T018 cannot, making the re-run appear redundant. | Add to T022 and T023: "verifies no warning escapes the `pytest.warns()` contexts under the global `error` filter — a regression not detectable in T012/T018 which ran without the global filter." |
| F19 | B — Ambiguity | **MEDIUM** | T025 | "if any appear, categorise and apply the appropriate Phase 3/4/5 fix pattern before proceeding" has no stopping criterion. If fixes introduce new warnings, this becomes an unbounded loop with no escalation path. | Define a gate: "if a newly discovered warning requires a new `ignore` entry not already in the spec exemptions table, stop, update the spec, and get review before adding the entry." |
| F20 | F — Inconsistency | **MEDIUM** | Plan §2 Technical Context "Key source files" | The plan's "Key source files" list mixes actual source files (`gh_cli_installer.py`, `session.py`, `helpers.py`) with a test file (`tests/unit/cli/copilot/session/test_start_copilot_session.py`). Test files are not source files. | Separate into two headings: "Key source files" and "Key test files." |
| F21 | C — Underspecification | **LOW** | Plan §4 Phase 4 note | The exemptions table is described as a "living record" with no stated ownership, update trigger, or governance (who adds entries? what review is required?). | Specify: "the spec §Known Third-Party Warning Exemptions table is the canonical record; any new `ignore` entry must be added there before being committed to `pyproject.toml`." |
| F22 | A — Duplication | **LOW** | Plan §5 Phase 5 success criteria checklist vs Spec §Success Criteria | The plan's Phase 5 contains a 6-item success criteria checklist that mirrors the spec's Success Criteria section nearly verbatim. The plan also duplicates task content of T024–T027. | Replace the checklist with a reference: "See spec §Success Criteria (SC1–SC6); tracked by tasks T024–T027." |
| F23 | B — Ambiguity | **LOW** | Spec Clarification #4 | "Unavoidable third-party warnings" is used as the criterion for `ignore` exemptions but is not defined. Two developers could disagree on whether a warning is "unavoidable." | Add a definition: "Unavoidable = emitted by a third-party library or Python stdlib on a code path that cannot be changed without forking the dependency or abandoning required functionality." |
| F24 | E — Coverage Gap | **LOW** | T016 | T016 is conditionally scoped to "any other test files identified in T004" with no fallback if T004 finds zero additional files. The task becomes silently vacuous with no explicit completion note. | Add: "If T004 identifies no additional files, mark T016 complete with note: 'No additional files found; T004 output confirms scope is limited to `test_start_copilot_session.py`.'" |
| F25 | C — Underspecification | **LOW** | T029 | T029 instructs to commit "tarfile fix, pytest.warns conversions, autopilot=False updates, and filterwarnings config in the body" but does not specify body formatting (bullet points vs prose) or require the `Co-authored-by` trailer mandated by the project's git commit convention. | Specify body format (e.g., "use bullet points per COMMIT_CONVENTION.md"); explicitly include the Co-authored-by trailer requirement. |

---

## 2. Coverage Summary Table

| Requirement Key | Has Task? | Task IDs | Notes |
|----------------|-----------|----------|-------|
| US1 — Fix `tarfile.extract()` DeprecationWarning at source | ✅ Yes | T007, T008, T009, T010, T011, T012 | Fully covered; T006/T010 merge recommended (F17) |
| US2 — Fix autopilot warning test patterns | ✅ Yes | T013, T014, T015, T016, T017, T018 | Covered; T013 has parallel-tag/dependency conflict (F07); T013/T004 duplication (F04) |
| US3 — Configure global `filterwarnings = ["error"]` | ✅ Yes | T019, T020, T021, T022, T023 | Covered; blocked on T003 completing first (F10) |
| FR1–FR6 (not individually enumerable — spec file is placeholder) | ⚠️ Partial | T007–T023 | Cannot verify FR-by-FR; all inferred FRs appear embedded in US task coverage (F01) |
| NFR: `pytest` exits 0 with `filterwarnings=["error"]` active | ✅ Yes | T024, T025 | |
| NFR: No `DeprecationWarning` from `tarfile` on Python 3.12+ | ✅ Yes | T012, T023 | NFR ID not annotated on tasks (F06) |
| NFR: No `UserWarning` from autopilot in non-intentional tests | ✅ Yes | T018, T022 | NFR ID not annotated on tasks (F06) |
| NFR: Intentional-warning tests use `pytest.warns()` | ✅ Yes | T014 | NFR ID not annotated (F06) |
| NFR: 100% coverage maintained | ⚠️ Conditional | T026 | Task is conditional ("if coverage drops"); should be unconditional verification |
| NFR: `run-pr-checks.sh` exits 0 | ✅ Yes | T027 | |
| EC1–EC5 (5 Edge Cases — not enumerable, spec unreadable) | ❌ No | — | Zero task coverage for any edge case (F05) |
| Known Third-Party Warning Exemptions table (spec §) | ⚠️ Partial | T003 | Table is empty in spec; T003 must populate before T019; no blocker enforced (F10) |
| Warning Audit Baseline (Phase 1 deliverable) | ✅ Yes | T001, T002, T003 | Output artifact destination unspecified (F12) |
| Warning Emission Site inventory | ⚠️ Partial | T005 | No output artifact location specified (F12) |
| `research.md` referenced by plan | ❌ No | — | No task validates or maintains this file (F16) |
| `# noqa: S202` annotation correctness | ❌ No | — | No task verifies the bandit rule is enabled before annotating (F15) |

---

## 3. Metrics

| Metric | Value |
|--------|-------|
| Total Named Requirements | 20 (3 US + 6 FR inferred + 6 NFR + 5 EC) |
| Total Tasks | 29 (T001–T029) |
| Requirements with ≥1 task | 15 / 20 |
| **Coverage %** | **75%** |
| Ambiguity Count (Pass B findings) | 7 (F02, F08, F09, F10, F15, F19, F23) |
| Duplication Count (Pass A findings) | 3 (F04, F18, F22) |
| Underspecification Count (Pass C) | 6 (F10, F12, F17, F21, F24, F25) |
| Constitution Issues (Pass D) | 2 (F01, F11) |
| Coverage Gaps (Pass E) | 5 (F05, F06, F16, F24 + NFR annotation gap) |
| Inconsistency Count (Pass F) | 7 (F02, F03, F07, F13, F14, F20 + match-string drift) |
| **Critical Issues** | **1** (F01 — spec file is a placeholder, not the actual document) |
| HIGH Severity Issues | 9 (F02–F10) |
| MEDIUM Severity Issues | 10 (F11–F20) |
| LOW Severity Issues | 5 (F21–F25) |
| **Total Findings** | **25** |

---
*Generated by Copilot SDK (gpt-5)*
