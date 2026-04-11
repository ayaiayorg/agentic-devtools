# Cross-Artifact Consistency & Quality Analysis — #1179 Enhance agdt-analyze-workflow

## 1. Findings Table

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| F01 | ~~C. Underspecification~~ | ~~**CRITICAL**~~ **RESOLVED** | `spec.md` | ~~The spec artifact is a meta-summary.~~ **Resolved**: `spec.md` now contains the full specification including 5 user stories with acceptance criteria, 16 functional requirements (FR-001–FR-016), 5 NFRs (NFR-001–NFR-005), 7 edge cases, 6 success criteria, dependencies, and out-of-scope section. Requirement-level traceability is now possible. | No further action needed. |
| F02 | ~~F. Inconsistency~~ | ~~**HIGH**~~ **RESOLVED** | Plan §1.3 vs tasks T024 | ~~**Contradictory "no external worktrees" behavior.**~~ **Resolved**: Plan §1.3 and T024 now both specify that `collect_external_context()` returns `None` when no external worktrees are found (`None` means "nothing to report", not an empty container). T024 test description reads: "no external worktrees returns `None` (consistent with `static_only` contract)". No contradiction remains. | No further action needed. |
| F03 | F. Inconsistency | **HIGH** → **N/A** | ~~data-model.md §5 vs §6~~ | ~~`ExternalContext` is defined as `@dataclass` (mutable) while all five other entities use `@dataclass(frozen=True)`.~~ **Not applicable**: `data-model.md` is not part of the committed artifacts for this PR. This finding should be re-evaluated if/when `data-model.md` is added. | Deferred — re-assess when `data-model.md` is committed. |
| F04 | ~~E. Coverage Gaps~~ | ~~**HIGH**~~ **RESOLVED** | spec.md (NFRs) → tasks.md | ~~Spec claims 5 NFRs with measurable metrics (backward compat, latency, read-only safety, error clarity, determinism). Only backward compatibility (T041–T043) has explicit tasks.~~ **Resolved**: Phase 5b now adds explicit tasks for latency (T050 — benchmark with upper-bound assertion), error clarity (T051 — assert error messages include specific parameter/path), and determinism (T052 — byte-identical output ordering test). Read-only safety remains partially covered by T024's write-call assertion. | No further action needed. |
| F05 | ~~E. Coverage Gaps~~ | ~~**HIGH**~~ **RESOLVED** | spec.md (edge cases) → tasks.md | ~~Spec claims 7 edge cases with exact error messages. No task validates that error messages match the specified text.~~ **Resolved**: T053 now tests all 7 edge cases (EC1–EC7) with exact error message string assertions where specified. T054 confirms these tests pass. | No further action needed. |
| F06 | ~~F. Inconsistency~~ | ~~**MEDIUM**~~ **RESOLVED** | Plan §1.2 (scan_identity_logs) vs Plan §1.2 (list_identity_directories) vs T015 vs T021 | ~~`list_identity_directories` does not mention `_unscoped` exclusion.~~ **Resolved**: Plan §1.2 now explicitly states `list_identity_directories` skips `_unscoped` (consistent with `scan_identity_logs`). T021 and T018 have been updated to document and test `_unscoped` exclusion. | No further action needed. |
| F07 | A. Duplication | **MEDIUM** | T006 / T045 | Both run `python scripts/validate_test_structure.py`. T006 is an early smoke test; T045 is a final gate. Same command, same purpose, no parameterization difference. | Keep T045 (final gate) and convert T006 to a "verify directories exist" check instead of full validator run, or simply note T006 is an early-exit guard. |
| F08 | A. Duplication | **MEDIUM** | T011 / T049 | Both verify imports with identical `python -c "from agentic_devtools.cli.analysis import …; print('OK')"`. T049 tests three functions; T011 tests three dataclasses — different symbols but same verification mechanism at two points. | Merge into a single final verification task (T049) that covers both dataclasses and functions. Remove T011 or reduce it to "no import errors" gate only. |
| F09 | A. Duplication | **MEDIUM** | T010 / T044 | T010: "Wire up `__init__.py` with all public exports." T044: "Update `__init__.py` exports to match all implemented public symbols." T044 is a re-do of T010 after implementation. | Rename T044 to "Verify `__init__.py` exports match implemented symbols" to clarify it's a review/audit step, not a re-implementation. |
| F10 | A. Duplication | **MEDIUM** | Plan §Phase 5 (Tasks 5.1–5.3) vs Plan §Phases 1.1–1.3 | Plan lists test files twice: once inside each Task description (e.g., Task 1.1 "Test files: test_resolve_analysis_context.py…") and again in Phase 5 ("Task 5.1: Test context_resolver.py functions — same files"). Tasks.md Phases 3–5 are the canonical location. | Remove Phase 5 from plan.md or convert it to "Run full suite" only (as T047 does). The per-module test descriptions in Phases 1.1–1.3 are sufficient. |
| F11 | C. Underspecification | **MEDIUM** | Plan §1.3 | `ExternalLogEvidence.excerpt` is "Max 500 lines" — no specification of **which** 500 lines (first? last? most recent?), nor what happens at the boundary (truncation marker?). T026 says "500-line excerpt truncation" without strategy. **Note:** `data-model.md` reference removed (not committed). | Specify: "last 500 lines (tail), with a `[…truncated {N} lines…]` header when truncation occurs." |
| F12 | F. Inconsistency | **MEDIUM** → **N/A** | ~~data-model.md §4 vs §6~~ | ~~`LogEvidence.modified_time` is `float` (epoch seconds). `ExternalLogEvidence.timestamp` is `str` (ISO-8601). Same semantic concept represented differently.~~ **Not applicable**: `data-model.md` is not part of the committed artifacts for this PR. | Deferred — re-assess when `data-model.md` is committed. |
| F13 | E. Coverage Gaps | **MEDIUM** | Dependency graph | The graph over-serializes independent work: T028 → T029 blocks SKILL.md schema edits on Python implementation completion. T032 → T033 blocks prompt updates on schema examples. Schema (JSON editing) and prompt (Markdown editing) are independent of Python code. | Allow Phases 6–7 to start in parallel with Phases 3–5 (only T036/T037 depend on schema completion, not all of T033–T038). |
| F14 | C. Underspecification | **MEDIUM** | Plan §1.1, T014 | `resolve_analysis_context` fallback case ("Neither → read current worktree_key from bootstrap") — no specification of behavior when bootstrap file doesn't exist or has no `worktree_key`. | Add edge case: "If bootstrap is absent or has no worktree_key, raise `RuntimeError` with message directing user to provide `--issue-key` or `--pr-id`." |
| F15 | B. Ambiguity | **LOW** | Plan §5 Risk Assessment | "Agent prompt too long for context window" listed as Medium likelihood — no measurable criteria. Current prompt is 351 lines; Phase 0 adds "~40 lines." No threshold defined for "too long." | Quantify: "Prompt must stay under 500 lines / 15k tokens to fit Copilot Chat context window." |
| F16 | ~~F. Inconsistency~~ | ~~**LOW**~~ **RESOLVED** | ~~Plan §1 ("352-line structured prompt") vs codebase (351 lines)~~ | ~~Minor off-by-one in line count.~~ **Resolved**: Plan §1 tech stack table now reads "351-line structured prompt", matching `wc -l .github/prompts/agdt.analyze-workflow.prompt.md` output. | No further action needed. |
| F17 | B. Ambiguity | **LOW** | T017 | "`.identity-owner` attribution" — unclear what this test validates. Does it check that `LogEvidence.identity` is populated from the `.identity-owner` file, or that the file's content (email) is included? | Clarify: the test should verify that `scan_identity_logs` sets `LogEvidence.identity` to the **directory name**, not the email from `.identity-owner`. The email is only used by `list_identity_directories`. |
| F18 | C. Underspecification | **LOW** | Plan §1.3 | `collect_external_context` calls `git worktree list --porcelain` — no specification of behavior when git is unavailable or the command fails (non-zero exit). | Add: "If `git worktree list` fails, log warning and return `None` (treat as no external worktrees)." |

---

## 2. Coverage Summary Table

> **Note:** The spec artifact now contains the full specification with FR-001–FR-016 and NFR-001–NFR-005 enumerated. Coverage is assessed against the **5 User Stories**, **16 FRs**, **5 NFRs**, and **7 edge cases**.

| Requirement Key | Has Task? | Task IDs | Notes |
|----------------|-----------|----------|-------|
| US1 — Parameterized invocation | ✅ Yes | T012–T016, T033, T038–T040 | Well covered across context resolver, prompt, agent definition |
| US2 — Multi-identity log scanning | ✅ Yes | T017–T023, T034 | Covered by identity_scanner tests + implementation + prompt update |
| US3 — External worktree context | ✅ Yes | T024–T028, T035 | Covered; F02 resolved — plan and tasks aligned on `None` return value |
| US4 — `external_context` schema field | ✅ Yes | T029–T032, T036–T037 | Schema + prompt + validation covered |
| US5 — Backward compatibility | ✅ Yes | T032, T041–T043 | Verification tasks present |
| NFR — Backward compatibility | ✅ Yes | T041–T043 | Explicit verification tasks |
| NFR — Latency | ✅ Yes | T050, T055 | Performance benchmark with upper-bound assertion (< 2s for ≤ 20 identity dirs) |
| NFR — Read-only safety | ⚠️ Partial | T024 (one assertion) | Only T024 mentions "assert no write calls"; no dedicated safety audit task |
| NFR — Error clarity | ✅ Yes | T051, T053 | Error message assertions include specific parameter/path; exact message strings tested |
| NFR — Determinism | ✅ Yes | T052, T056 | Byte-identical JSON output ordering test across consecutive calls |
| FR-001–FR-016 | ✅ Yes | Various | FRs now enumerated in spec.md (F01 resolved); traceability restored |
| Edge cases (7) | ✅ Yes | T053, T054 | All 7 edge cases (EC1–EC7) have explicit test assertions with exact error messages |

---

## 3. Metrics

| Metric | Value |
|--------|-------|
| **Total Requirements (visible)** | 5 US + 16 FRs + 5 NFRs + 7 edge cases = 33 total (all now enumerated in spec.md) |
| **Total Tasks** | 56 (T001–T056) |
| **User Story Coverage** | 100% (5/5 US have tasks) |
| **NFR Coverage** | 80% (4/5 NFRs fully covered; 1 partial — read-only safety) |
| **Edge Case Coverage** | 100% (7/7 explicitly tested in T053) |
| **Overall Traceable Coverage** | ~90% of requirements have adequate task coverage |
| **Ambiguity Count** | 2 (F15, F17) |
| **Duplication Count** | 4 (F07, F08, F09, F10) |
| **Critical Issues Count** | 0 (F01 resolved) |
| **High Issues Count** | 0 (F02, F04, F05 resolved; F03 N/A) |
| **Medium Issues Count** | 5 (F07–F11, F13–F14; F06 resolved, F12 N/A) |
| **Low Issues Count** | 3 (F15, F17, F18; F16 resolved) |
| **Total Findings** | 18 (7 resolved/N/A, 11 active) |

---
*Generated by Copilot SDK (claude-opus-4.6)*
