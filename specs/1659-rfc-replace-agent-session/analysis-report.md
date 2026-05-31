# Cross-Artifact Consistency & Quality Analysis Report

## Findings Table

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| F-01 | F | MEDIUM | Plan Phase 1 Task 4 vs Spec FR-006 | FR-006 already requires determining which sessions are new, but module ownership is ambiguous: plan assigns `determine_new_sessions` to `merger.py` while FR-006 only lists `parser.py`, `renderer.py`, `merger.py`, `models.py` | Add explicit note in FR-006 that new-session determination logic belongs in `merger.py` |
| F-02 | C | MEDIUM | Spec NFR-001 | Round-robin cursor storage mechanism unspecified — plan says "cache artifact" but spec says "repository-level cursor managed by the monitor (not per-PR tracker comments)" without defining persistence format | Specify cursor persistence mechanism (Actions cache key, workflow artifact, or environment variable) in spec |
| F-03 | B | MEDIUM | Spec NFR-005 | "Retry logic with exponential backoff (minimum 3 attempts with 2-second base delay)" — existing `cli/ci/retry.py` already provides `retry_with_backoff`; spec doesn't reference reuse | Clarify whether NFR-005 requires new retry logic or reuse of existing `cli/ci/retry.py` module |
| F-04 | F | LOW | Tasks T040 vs T047 | T040 says "Remove `actions/cache` steps" while T047 says "persist cursor via cache artifact" — potentially contradictory use of Actions cache | T040 description already clarifies "preserve any cache steps used for non-deduplication state" — no action needed, but verify T047 uses a distinct cache key |
| F-05 | C | MEDIUM | Spec FR-004 | Reviews API polling specifies detecting "reviews authored by the Copilot bot on the current head commit" but doesn't specify exact bot login names to match (e.g., `copilot-pull-request-reviewer[bot]`, `Copilot`) | Add explicit list of Copilot bot login names to match in FR-004 or reference existing constants |
| F-06 | D | LOW | Spec | No explicit "Out of Scope" section listing what this feature intentionally does NOT cover (e.g., non-GitHub providers, multi-repo support) | Add Out of Scope section for clarity |
| F-07 | F | MEDIUM | Spec FR-011 vs Tasks | FR-011 mentions updating `tests/workflows/test_agent_session_monitor.py` to add assertions for "batching" but no task explicitly covers adding a batching assertion test beyond T052 (env var presence) | Add explicit task or expand T052 to cover batch behavior assertions |
| F-08 | C | LOW | Plan Phase 3 Task 4 | "Add Reviews API polling" step lacks detail on how to determine "current head SHA" for filtering reviews — is it read from PR API or passed as input? | Specify head SHA resolution mechanism (e.g., from `gh pr view --json headRefOid`) |
| F-09 | G | HIGH | T031, T061 | T031: "Grep repository for references to deleted files and remove all references" — T061: "Verify no remaining references to deleted files via grep" — same grep for same files, T061 is a verification of T031's work | See Category G findings below |
| F-10 | G | HIGH | T007, T014 | T007: "Write failing tests for `parser.py`" includes "malformed HTML header" — T014: "Write failing tests for parser/renderer round-trip losslessness" — both target parser test directory with overlapping scope on parser behavior | See Category G findings below |
| F-11 | G | HIGH | T027, T055 | T027: "Write test asserting `pull_request_review` is NOT in `ai-pr-loop.yml` triggers" — T055: "Add test asserting workflow only has `schedule` and `workflow_dispatch` triggers (no `pull_request_review`)" — same assertion, different test files | See Category G findings below |
| F-12 | E | LOW | NFR-002 | NFR-002 (atomic comment update) has no dedicated test task — it's implicitly covered by T022 (concurrent merge) and T043 (upsert) but no test explicitly validates atomicity guarantee | Consider adding explicit atomicity test or documenting T022 as NFR-002 coverage |

### Category G Structured Findings

[
  {
    "id": "G-01",
    "overlap_type": "overlapping",
    "severity": "HIGH",
    "task_ids": ["T031", "T061"],
    "dimensions": ["description"],
    "rationale": "T031 removes references to deleted files; T061 runs the same grep to verify none remain. Intent differs, but the grep step is duplicated."
  },
  {
    "id": "G-02",
    "overlap_type": "overlapping",
    "severity": "HIGH",
    "task_ids": ["T007", "T014"],
    "dimensions": ["file_path"],
    "rationale": "Both tasks target tests under tests/unit/cli/ci/tracker/parser/. They cover different parser behaviors, but overlap on the same test area/module."
  },
  {
    "id": "G-03",
    "overlap_type": "overlapping",
    "severity": "HIGH",
    "task_ids": ["T027", "T055"],
    "dimensions": ["description"],
    "rationale": "Both tasks assert that ai-pr-loop.yml does not use pull_request_review triggers; they differ only in which test file hosts the assertion."
  }
]

## Coverage Summary Table

| Requirement Key | Has Task? | Task IDs | Notes |
|----------------|-----------|----------|-------|
| FR-001 | ✅ | T041, T042, T053 | Covered |
| FR-002 | ✅ | T013, T019, T021, T022, T040, T043, T054 | Covered |
| FR-003 | ✅ | T044, T055 | Covered |
| FR-004 | ✅ | T024, T025, T026, T027, T055 | Covered |
| FR-005 | ✅ | T028, T029, T030, T031, T032, T033, T061 | Covered |
| FR-006 | ✅ | T001-T006, T010-T012, T023, T034-T036, T038, T056, T057, T062 | Covered |
| FR-007 | ✅ | T006, T007, T008, T010, T011, T014, T043 | Covered |
| FR-008 | ✅ | T039, T051 | Covered |
| FR-009 | ✅ | T046, T053 | Covered |
| FR-010 | ✅ | T009, T012, T017, T018 | Covered |
| FR-011 | ✅ | T027, T032, T033, T051-T055 | Covered |
| FR-012 | ✅ | T015, T016 | Covered |
| NFR-001 | ✅ | T047, T052 | Covered |
| NFR-002 | ⚠️ | T022, T043 | Implicit only — no explicit atomicity test |
| NFR-003 | ✅ | T056 | Covered |
| NFR-004 | ✅ | T019, T020 | Covered |
| NFR-005 | ✅ | T048 | Covered |
| NFR-006 | ✅ | T049 | Covered |

## Metrics

| Metric | Value |
|--------|-------|
| Total Requirements | 18 (12 FR + 6 NFR) |
| Total Tasks | 62 |
| Coverage % | 94% (17/18 — NFR-002 implicit only) |
| Ambiguity Count | 1 (F-03) |
| Requirement Duplication Count (Category A) | 0 |
| Critical Issues Count | 0 |
| Task Deduplication Finding Count | 3 |
| Task Deduplication by Type | duplicate: 0 / overlapping: 3 / conflicting: 0 |
| Multi-Task Group Count | 0 |

## Next Actions

No CRITICAL issues were found. The following improvements are recommended before proceeding to implementation:

- **F-01 / F-07** (MEDIUM): Clarify module placement for `determine_new_sessions` in FR-006
  and add an explicit batching assertion task or expand T052. Run `/speckit.agdt:specify`
  with refinement if changes are needed.
- **F-02 / F-05** (MEDIUM): Specify cursor persistence mechanism in NFR-001 and add explicit Copilot bot login names to FR-004. These can be manually edited in `spec.md`.
- **F-03** (MEDIUM): Decide whether NFR-005 reuses `cli/ci/retry.py` or introduces new retry logic; update spec accordingly.
- **G-01 / G-02 / G-03** (HIGH overlapping): Review duplicated test steps across T031/T061, T007/T014, and T027/T055. Consider consolidating or annotating to avoid double-coverage confusion.

You may proceed to `/speckit.agdt:implement` with the current artifacts. Would you like me to suggest concrete remediation edits for the top issues listed above?

---

*Generated by Copilot SDK (claude-opus-4.6)*
