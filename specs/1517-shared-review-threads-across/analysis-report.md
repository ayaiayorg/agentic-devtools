# Analysis Report: Shared Review Threads Across Identities (#1517)

## Findings Table

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| F-01 | F | HIGH | Plan Phase 4 / Task T026 | **Function signature mismatch**: Plan defines `discover_reusable_threads(threads, pull_request_id, target_files)` with 3 params; T026 implements `discover_reusable_threads(threads, target_files)` with only 2 params, omitting `pull_request_id`. | Align T026 signature with the plan, or update the plan if `pull_request_id` is not needed (note: `sync_review_state_from_threads` uses it for cross-contamination filtering). |
| F-02 | E | HIGH | Plan Phase 4 / Tasks | **`_incremental_rescaffold()` modification missing from tasks**: Plan Phase 4 explicitly calls for applying discovery logic in `_incremental_rescaffold()` for new files, but no task covers this function. Only `_fresh_scaffold()` is addressed (T038, T044, T050). | Add tasks for integrating discovery into `_incremental_rescaffold()` or document why incremental rescaffolding is excluded. |
| F-03 | E | MEDIUM | NFR-001 / Tasks | **NFR-001 (latency ≤200ms p95) has no test task**: No task validates the performance requirement. The spec asserts single-pass reuse of `classify_agdt_threads()` as mitigation, but no benchmark or assertion exists. | Add a task (or note in an existing edge-case task) that asserts classification + discovery completes within the 200ms budget for a 500-thread fixture. |
| F-04 | E | MEDIUM | FR-004, FR-007, FR-008 / Coverage data | **Missing happy-path tests for P2 requirements**: Pre-validated coverage shows `has_happy_path: false` for FR-004 (classification), FR-007 (mixed scenarios), and FR-008 (backward compat). US4 and US5 define clear happy-path acceptance scenarios that should map to explicit happy-path test tasks. | Promote T025 (FR-004), T055 (FR-007), and a backward-compatibility task such as T054 or T056 (FR-008) to explicit happy-path tests in their task descriptions, or add dedicated happy-path tasks. |
| F-05 | F | MEDIUM | Dependencies table / T004–T006 | **Incorrect dependency**: T004–T006 are declared as depending on T002 (creates `tests/unit/cli/azure_devops/thread_reuse/`), but T004–T006 create tests under `tests/unit/cli/azure_devops/review_state/` which already exists. | Remove the T002 dependency from T004–T006; they have no blocking prerequisite. |
| F-06 | G | CRITICAL | T038, T044, T050 | **Overlapping scaffold modifications**: All three tasks modify `_fresh_scaffold()` in `review_scaffold.py` to add thread-type-specific reuse logic. While intentionally incremental (activity-log → overall → file), they share file path and code section. | Document that these are sequential/additive modifications to the same function. No merge needed — the TDD ordering is correct — but implementers must be aware of merge conflicts if tasks are parallelized. |
| F-07 | B | LOW | Spec FR-005 | **"first adopted" is slightly ambiguous**: FR-005 says `originalAuthorId` records the author "when first discovered/adopted" — clarify whether this means first scaffolded by any identity, or first reused by a different identity. | Clarify: `originalAuthorId` is set from the first comment's `author.id` at the time the thread is first recorded in review state (whether newly created or reused). |
| F-08 | C | LOW | Plan Phase 3 / Tasks T033 | **Session ID source unspecified in spec**: The reuse correlation marker uses `session:{session_id}` but the spec does not define where the session ID comes from. The plan and tasks assume it exists but don't trace its source. | Add a note in T033 or the plan clarifying the session ID source (likely `ReviewSession` or `copilot.session_id` from state). |

### Category G Structured Findings

[
  {
    "id": "F-06",
    "overlap_type": "overlapping",
    "severity": "CRITICAL",
    "task_ids": ["T038", "T044", "T050"],
    "dimensions": ["file_path", "code_section"],
    "rationale": "All three tasks modify _fresh_scaffold() in review_scaffold.py and overlap on both file path and code section while incrementally adding thread-type-specific reuse logic."
  }
]

## Coverage Summary Table

| Requirement Key | Has Task? | Task IDs | Notes |
|----------------|-----------|----------|-------|
| FR-001 | ✅ | T036, T037, T038, T039, T040 | Activity-log reuse; well-covered |
| FR-002 | ✅ | T041, T042, T044, T046 | Overall-summary reuse; well-covered |
| FR-003 | ✅ | T047, T048, T050, T052, T053 | File-summary reuse; well-covered |
| FR-004 | ✅ | T021–T030, T069 | Classification/matching; no happy-path test (edge-case only) |
| FR-005 | ✅ | T004, T005, T016, T043, T045, T049, T051, T058 | originalAuthorId persistence; well-covered |
| FR-006 | ✅ | T031, T032, T035, T036, T039, T041, T044, T047, T050, T061, T068 | No-duplicate + reuse-reply; extensively covered |
| FR-007 | ✅ | T052, T055, T059, T062, T065, T066, T067 | Mixed/partial scenarios; no explicit happy-path test |
| FR-008 | ✅ | T006, T054, T056, T057, T058, T060 | Backward compat; no happy-path test (edge-case and infrastructure only) |
| NFR-001 | ❌ | — | No latency validation task |
| NFR-002 | ✅ | T061, T063 | Logging; covered |
| NFR-003 | ✅ | T032, T034, T068 | Idempotency; covered |

## Metrics

| Metric | Value |
|--------|-------|
| Total Requirements | 11 (8 FR + 3 NFR) |
| Total Tasks | 73 |
| Coverage % | 91% (10/11 requirements have tasks; NFR-001 uncovered) |
| Ambiguity Count | 1 |
| Requirement Duplication Count (Category A) | 0 |
| Critical Issues Count | 1 |
| Task Deduplication Finding Count | 1 |
| Task Deduplication by Type | duplicate: 0 / overlapping: 1 / conflicting: 0 |
| Multi-Task Group Count | 1 (3-task group: T038, T044, T050) |

---
*Generated by Copilot SDK (claude-opus-4.6)*

### Next Actions

- Resolve CRITICAL finding F-06 before `/speckit.agdt:implement` to avoid parallel-change conflicts in `_fresh_scaffold()`.
- Manually update `tasks.md` sequencing notes to mark T038, T044, and T050 as same-function additive edits requiring strict serial execution.

Would you like me to suggest concrete remediation edits for the top 3 issues?
