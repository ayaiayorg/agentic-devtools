# Cross-Artifact Consistency & Quality Analysis Report

## 1. Findings Table

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| F-01 | Inconsistency | HIGH | Plan §Research Summary vs. Spec §Clarified decisions #5, FR-006; Tasks T002, T015–T023 | Plan says agent files use `.specify/memory/` filesystem path; spec and task list both say `/memory/markdown-rules.md` virtual path | Correct plan research summary to align with spec decision #5 and task list |
| F-02 | Inconsistency | MEDIUM | Plan §Phases (T01–T27) vs. Tasks (T001–T039) | Plan defines 27 tasks with IDs T01–T27; task list defines 39 tasks with IDs T001–T039. No cross-reference mapping exists | Add a plan↔task traceability mapping or adopt a single numbering scheme |
| F-03 | Coverage Gap | MEDIUM | NFR-003 | NFR-003 (Clarity) has no associated verification task — no task checks that shared-file or instruction wording is "unambiguous" for maintainers | Add a verification task for NFR-003 or fold a clarity check into T037 |
| F-04 | Ambiguity | MEDIUM | NFR-003 | "Unambiguous" is subjective with no measurable criterion | Define a concrete test (e.g., "a new maintainer can identify the rule source within 30 seconds") or remove the NFR and rely on review |
| F-05 | Ambiguity | MEDIUM | SC-007 | "ideally on the initial generation pass" weakens SC-007 to aspirational; T036 treats it as a hard pass/fail check | Decide whether SC-007 is a hard gate or a best-effort goal; update SC or T036 to match |
| F-06 | Duplication | LOW | FR-004, FR-008 | FR-004 requires the one-line load instruction; FR-008 requires it be placed in context/setup section — overlapping scope | Consolidate into a single FR with placement specified, or mark FR-008 as a refinement of FR-004 |
| F-07 | Duplication | LOW | FR-002, FR-005 | Both establish `.specify/memory/markdown-rules.md` as the canonical location; FR-005 only adds that the constitution is not primary | Merge FR-005 as a note/constraint on FR-002 |
| F-08 | Coverage Gap | MEDIUM | Edge case #2 ("Constitution also contains related guidance") | No task audits or reconciles existing constitution wording with the new shared file | Add a task to review constitution for overlapping fenced-code-block guidance and document the relationship |
| F-09 | Underspecification | MEDIUM | Spec (no section); Tasks T005 | The exact format/wording of the one-line load instruction is unspecified beyond a 100-char limit; T005 says "draft" it but no AC defines valid instruction text | Add an acceptance criterion or example for the load instruction format (e.g., must begin with a verb like "Load" and reference the virtual path) |
| F-10 | Underspecification | LOW | Spec §Scope ("pipeline/runtime prompt assembly path") | Spec refers to "the pipeline/runtime prompt assembly path" as a singular concept; actual artifacts are two distinct scripts in bash and PowerShell | Name both scripts in the spec scope section for precision |
| F-11 | Coverage Gap | MEDIUM | Edge case #2; Tasks | No task verifies that the shared file remains authoritative when constitution contains similar wording | Add explicit verification task or fold into T028 |
| F-12 | Underspecification | LOW | FR-001, FR-007 | FR-001 specifies `cat`/`Get-Content -Raw` but does not define the error detection mechanism (e.g., checking exit code vs. testing file existence before reading) | Specify whether scripts should use file-existence checks or trap non-zero exit codes |
| F-13 | Ambiguity | LOW | FR-007 | "Log a clear warning to stderr" — "clear" is subjective; no required format or content is specified | Define minimum warning content (e.g., must include missing file path and a remediation hint) |
| F-14 | Underspecification | MEDIUM | Spec §Scope; Plan; Tasks T001 | Spec uses glob patterns ("all files matching…") but plan/tasks hardcode a count of 9+9. If files are added between planning and implementation, coverage is silently incomplete | Change tasks to use glob-based verification (e.g., "all files matching pattern have instruction") rather than hardcoded counts |
| F-15 | Coverage Gap | HIGH | Spec §Clarified decisions #5 | Spec requires "agent runtimes must provide the same `/memory/*` mapping" but no task verifies this runtime capability exists | Add a verification task confirming agent runtimes resolve `/memory/markdown-rules.md` correctly |
| F-16 | Inconsistency | MEDIUM | Tasks T002 | T002 main text studies the `.specify/memory/constitution.md` filesystem-path pattern in agent files, but the parenthetical note says the new file will use the virtual path — a deliberate departure from the studied pattern, buried in a parenthetical | Promote the virtual-path decision to T002's main description; note the departure from the constitution pattern explicitly |
| F-17 | Underspecification | LOW | US3 AC #3 | US3 AC says "degrades gracefully and does not crash unexpectedly" without specifying observable output; FR-007 supplements with stderr logging but the AC itself is incomplete | Update US3 AC #3 to reference FR-007's stderr warning requirement |

## 2. Coverage Summary Table

| Requirement Key | Has Task? | Task IDs | Notes |
|----------------|-----------|----------|-------|
| FR-001 | ✅ | T024, T026 | Bash and PowerShell injection covered separately |
| FR-002 | ✅ | T003 | File creation |
| FR-003 | ✅ | T003 | Normative content included in creation task |
| FR-004 | ✅ | T006–T014 | 9 command templates |
| FR-005 | ⚠️ | T003 (implicit) | No dedicated verification that constitution is not primary; partially implied by T003/T028 |
| FR-006 | ✅ | T015–T023 | 9 agent files |
| FR-007 | ✅ | T025, T027, T039 | Both scripts + E2E degradation test |
| FR-008 | ✅ | T006–T014, T015–T023 | Placement specified per-file |
| NFR-001 | ✅ | T004, T005, T031 | Size validation for file, reference, and combined |
| NFR-002 | ✅ | T037 | No-duplication check |
| NFR-003 | ❌ | — | No clarity verification task (see F-03) |
| SC-001 | ✅ | T028 | File existence check |
| SC-002 | ✅ | T029 | Command template coverage |
| SC-003 | ✅ | T030 | Agent file coverage |
| SC-004 | ✅ | T031 | Size budget verification |
| SC-005 | ✅ | T032 | Standalone-spec verification |
| SC-006 | ✅ | T033, T034 | Bash and PowerShell separately |
| SC-007 | ✅ | T036 | MD040 lint check (but SC wording is aspirational — see F-05) |
| Edge: Missing file | ✅ | T025, T027, T039 | Covered |
| Edge: Constitution overlap | ❌ | — | No task (see F-08, F-11) |
| Edge: Non-code blocks | ✅ | T003 | Fallback to `text` in normative rule |
| Edge: Partial rollout | ✅ | T029, T030, T035 | Full-coverage verification |
| Clarified decision #5 (runtime mapping) | ❌ | — | No task verifies agent runtimes resolve virtual path (see F-15) |

## 3. Metrics

| Metric | Value |
|--------|-------|
| **Total Requirements (FR + NFR)** | 11 |
| **Total Success Criteria** | 7 |
| **Total Tasks** | 39 |
| **Requirement → Task Coverage** | 91% (10/11; NFR-003 uncovered) |
| **Success Criteria → Task Coverage** | 100% (7/7) |
| **Edge Case → Task Coverage** | 75% (3/4; constitution overlap uncovered) |
| **Overall Trackable-Item Coverage** | 91% (21/23 trackable items have ≥1 task) |
| **Ambiguity Count** | 4 (F-04, F-05, F-13, plus SC-007 qualifier) |
| **Duplication Count** | 2 (F-06, F-07) |
| **Critical Issues Count** | 0 |
| **High Issues Count** | 2 (F-01, F-15) |
| **Medium Issues Count** | 9 |
| **Low Issues Count** | 6 |
| **Total Findings** | 17 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
