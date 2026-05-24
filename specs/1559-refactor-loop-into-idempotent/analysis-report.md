# Analysis Report: Idempotent Action Evaluator for AI PR Loop

## Findings Table

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| F-01 | Duplication | LOW | FR-002 / US1-AC2 | FR-002 states idempotency (no duplicate side effects on N runs) and US1-AC2 restates the same requirement ("every action evaluates as skipped and no mutating API calls are made"). | Keep both; they serve different audiences (requirement vs. testable scenario). No action needed. |
| F-02 | Ambiguity | MEDIUM | NFR-001 | "Normal conditions (excluding external API latency spikes beyond 10 seconds per call)" — what constitutes "normal" is not defined beyond the API exclusion. Number of threads, commit count, or PR size could affect runtime. | Add a reference workload profile (e.g., "≤20 unresolved threads, ≤50 commits, ≤100 changed files"). |
| F-03 | Ambiguity | MEDIUM | FR-004 | "SDK verification" is referenced but never defined — which SDK, what verification protocol, what are the possible verdicts beyond `COMMENT_RESOLVE`? | Add a brief definition or cross-reference to existing SDK verification logic in the codebase. |
| F-04 | Ambiguity | LOW | NFR-002 | "< 2000 characters for the visible portion" — unclear whether this counts markdown source or rendered text, and whether the sentinel HTML comment counts. | Specify: markdown source bytes excluding the sentinel line and the `<details>` block. |
| F-05 | Underspecification | MEDIUM | FR-008 / T045 | The spec states the summary must include a "collapsed state snapshot section" but does not define which fields from `PRStateSnapshot` to include or their format. | Define a minimum field set (e.g., head_sha, commit_count, ci_status, is_draft, active_session, unresolved_thread_count). |
| F-06 | Underspecification | MEDIUM | Edge Cases | "Existing evaluator lock mechanism must gate the entire pipeline" — no specification of lock timeout, retry behavior, or lock storage mechanism for the new pipeline context. | Specify lock timeout (e.g., 120s matching NFR-001) and confirm reuse of existing file/API-based lock. |
| F-07 | Underspecification | MEDIUM | FR-011 / T010 | `build_pr_state_snapshot()` gathers "all PR state in one pass" but does not specify which provider methods are called or error handling if one sub-query fails. | Specify whether partial snapshot failure aborts the run or uses defaults for missing fields. |
| F-08 | Constitution Alignment | LOW | Spec | No explicit "Out of Scope" section listing what the feature intentionally does NOT cover (e.g., multi-repo support, non-GitHub providers). | Add an "Out of Scope" section for clarity. |
| F-09 | Coverage Gaps | MEDIUM | NFR-005 | NFR-005 (backward compatibility with `EventPayload`, `PRMetadata`, `ReviewInfo`) has task T063 but no dedicated test task verifying the dataclass interfaces remain unchanged. | Add a test task specifically asserting backward-compatible signatures/fields of these dataclasses. |
| F-10 | Inconsistency | MEDIUM | Plan Phase 2 vs Tasks Phase 2 | Plan Phase 2 is titled "Implement Actions 1–4" but Tasks Phase 2 is "Foundational — Core Types & Infrastructure". The phase mapping table clarifies this but creates confusion when reading the plan linearly. | Rename plan phases or add explicit cross-references in both documents. |
| F-11 | Inconsistency | LOW | Plan §4.2 Task 3 / T019 | Plan Phase 2 Task 3 for `publish.py` says "Execute: squash_before_publish + publish_pr" but T019 only mentions "update DerivedState on execute" without referencing squash_before_publish. | Ensure T019 description includes the squash-before-publish step from the plan. |
| F-12 | Inconsistency | LOW | T056 vs T029 | T056 (Phase 8) implements "ApproveAction HEAD SHA verification" but T029 (Phase 3) already implements `ApproveAction` with precondition "no approval on current HEAD SHA". These overlap in scope. | Clarify T056 as hardening/re-validation within execute() vs T029's precondition check in evaluate(). |
| G-01 | Task Deduplication | CRITICAL | T029, T056 | T029 implements ApproveAction with "no approval on current HEAD SHA" precondition; T056 implements "HEAD SHA verification ensuring approval targets current commit". Same action, same file, overlapping logic. | Clarify T056 scope as execute-time re-validation distinct from T029's evaluate-time precondition. |
| G-02 | Task Deduplication | CRITICAL | T025, T058 | T025 implements DispatchRepairAction with "dedup/cycle limits" precondition; T058 implements "cycle/deduplication limit checks within DispatchRepairAction preconditions". Same file, same logic. | Merge T058 into T025 or clarify T058 as hardening of already-implemented T025 logic. |
| G-03 | Task Deduplication | CRITICAL | T033, T069 | T033: "run pipeline twice on unchanged state → 0 duplicate API calls"; T069: "50 consecutive runs on unchanged state → 0 duplicate API calls". Same intent (idempotency verification), same test scope. | Keep T069 as the stronger version (50 runs); remove or subsume T033 into T069. |
| G-04 | Task Deduplication | CRITICAL | T034, T070 | T034: "all 8 actions evaluated regardless of trigger type"; T070: "3 trigger types produce identical evaluations". Same test intent, same runner scope. | Keep T070 as the stricter version (identical evaluations); remove or subsume T034. |
| G-05 | Task Deduplication | CRITICAL | T040, T067 | T040: "test verifying zero references to squash-wait markers in production code"; T067: "Verify zero references to squash-wait markers in all production files". Identical verification. | Remove one; T067 (Phase 10) can serve as the final validation if T040 is removed. |
| G-06 | Task Deduplication | CRITICAL | T023-T024, T041-T042 | T023 implements ResolveThreadsAction with preconditions (no active session, no pending review, threads exist); T041-T042 add "SDK verification logic" and "ensure both conditions checked" to the same file. T024 and T043-T044 test the same action. | Clarify T041-T042 as extending T023's execute() method (not reimplementing preconditions). Consolidate test tasks or clearly scope T043-T044 to new SDK logic only. |

## Coverage Summary Table

| Requirement Key | Has Task? | Task IDs | Notes |
|----------------|-----------|----------|-------|
| FR-001 | Yes | T013, T014, T017–T034, T060–T066, T068, T070, T072 | Extensively covered |
| FR-002 | Yes | T019–T032, T033, T069 | Covered; T033/T069 overlap |
| FR-003 | Yes | T015, T016, T035, T036 | Covered |
| FR-004 | Yes | T041, T043, T044 | Covered |
| FR-005 | Yes | T023, T024, T035, T036, T042, T043 | Covered |
| FR-006 | Yes | T027, T028, T035, T036 | Covered |
| FR-007 | Yes | T031, T032, T057, T059 | Covered |
| FR-008 | Yes | T045–T051 | Covered |
| FR-009 | Yes | T013, T014, T052–T055 | Covered |
| FR-010 | Yes | T037–T040, T067 | Covered; T040/T067 overlap |
| FR-011 | Yes | T008–T011 | Covered |
| FR-012 | Yes | T029, T030, T056, T059 | Covered; T029/T056 overlap |
| FR-013 | Yes | T025, T026, T058, T059 | Covered; T025/T058 overlap |
| FR-014 | Yes | T013, T014, T017, T018 | Covered |
| NFR-001 | Yes | T068 | Single validation task |
| NFR-002 | Yes | T045, T048 | Covered via render tests |
| NFR-003 | Yes | T013, T014, T050 | Covered |
| NFR-004 | Yes | T064, T066 | Covered |
| NFR-005 | Yes | T063 | No dedicated interface test |
| NFR-006 | Yes | T052, T055 | Covered |

## Metrics

| Metric | Value |
|--------|-------|
| Total Requirements | 20 (14 FR + 6 NFR) |
| Total Tasks | 73 |
| Coverage % | 100% (all FRs and NFRs have at least one task) |
| Ambiguity Count | 3 (F-02, F-03, F-04) |
| Requirement Duplication Count (Category A) | 1 |
| Critical Issues Count | 6 |
| Task Deduplication Finding Count | 6 |
| Task Deduplication by Type | duplicate: 0 / overlapping: 6 / conflicting: 0 |
| Multi-Task Group Count | 1 (G-06 involves 6 tasks) |

### Category G Structured Findings

[
  {
    "id": "G-01",
    "overlap_type": "overlapping",
    "severity": "CRITICAL",
    "task_ids": [
      "T029",
      "T056"
    ],
    "dimensions": [
      "description",
      "file_path"
    ],
    "rationale": "T029 adds evaluate-time HEAD SHA checks for ApproveAction, while T056 adds execute-time HEAD SHA verification in the same action file. Both target approval-on-current-HEAD logic."
  },
  {
    "id": "G-02",
    "overlap_type": "overlapping",
    "severity": "CRITICAL",
    "task_ids": [
      "T025",
      "T058"
    ],
    "dimensions": [
      "description",
      "file_path"
    ],
    "rationale": "T025 and T058 both implement dedup/cycle limit preconditions for DispatchRepairAction in the same file. The described behavior is nearly identical, so T058 appears to restate T025."
  },
  {
    "id": "G-03",
    "overlap_type": "overlapping",
    "severity": "CRITICAL",
    "task_ids": [
      "T033",
      "T069"
    ],
    "dimensions": [
      "description",
      "code_section"
    ],
    "rationale": "T033 and T069 both verify idempotency by asserting no duplicate API calls on unchanged state. T069 is a stronger superset of T033 (50 runs vs 2) in the same runner test scope."
  },
  {
    "id": "G-04",
    "overlap_type": "overlapping",
    "severity": "CRITICAL",
    "task_ids": [
      "T034",
      "T070"
    ],
    "dimensions": [
      "description",
      "code_section"
    ],
    "rationale": "T034 and T070 both validate trigger-agnostic action evaluation in the same runner tests. T070 is the stronger assertion because it requires identical evaluations across trigger types."
  },
  {
    "id": "G-05",
    "overlap_type": "overlapping",
    "severity": "CRITICAL",
    "task_ids": [
      "T040",
      "T067"
    ],
    "dimensions": [
      "description",
      "file_path"
    ],
    "rationale": "T040 and T067 both verify zero squash-wait marker references across production files under agentic_devtools/. They target the same verification outcome with overlapping file scope."
  },
  {
    "id": "G-06",
    "overlap_type": "overlapping",
    "severity": "CRITICAL",
    "task_ids": [
      "T023",
      "T024",
      "T041",
      "T042",
      "T043",
      "T044"
    ],
    "dimensions": [
      "description",
      "file_path"
    ],
    "rationale": "T023/T024 and T041-T044 all modify or test ResolveThreadsAction in the same file/test area. Preconditions, SDK checks, and repeated tests overlap without clear evaluate/execute boundaries."
  }
]

---

## Next Actions

- Prioritize the MEDIUM/HIGH-severity ambiguities and overlaps for spec cleanup before implementation begins.
- Clarify acceptance details for FR-004, FR-008, FR-011, NFR-001, and NFR-002 so tasks and tests can be derived unambiguously.
- Consolidate or retire overlapping tasks called out in the overlap analysis, especially where one task is a strict superset of another.
- Add explicit coverage for backward-compatibility verification and define out-of-scope boundaries to reduce future planning churn.

Would you like me to suggest concrete remediation edits for the spec and task list to address the issues above?

---
*Generated by Copilot SDK (claude-opus-4.6)*
