# Cross-Artifact Consistency & Quality Analysis Report

## Findings Table

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| F-01 | B | MEDIUM | Spec FR-017, Plan Todo 3.1 | "Staged remediation pattern used by sibling spec #1191" — no detail on what this pattern entails; readers must cross-reference an external spec to understand retry behavior | Add a 1–2 sentence inline description of the staged pattern (e.g., "Stage 1: re-prompt with original prompt + failure context; Stage 2: re-prompt with explicit formatting constraints") |
| F-02 | C | MEDIUM | Spec FR-001, Plan Todo 2.1 | FR-001 references `**Source Issue**` marker but does not specify the exact regex or matching format (e.g., must it be `**Source Issue**: #<number>` or just contain `#<number>` anywhere?) | Specify the exact text pattern the validator searches for (e.g., `**Source Issue**: https://github.com/.../issues/<N>` or `#<N>`) |
| F-03 | F | LOW | Plan Todo 2.2 vs Spec FR-020 | Plan says `_resolve_paths()` raises `SystemExit(1)` for explicit missing files, but FR-020 says zero-match globs exit with code 0. The distinction is clear in the plan but the spec FR-020 only mentions "glob patterns resolve to zero files" without explicitly stating explicit paths should fail — could cause implementer confusion | Add a note to FR-020 or a new FR clarifying that explicit (non-glob) paths that don't exist are blocking failures (exit 1) |
| F-04 | A | LOW | Spec AC-12 vs FR-001 | AC-12 largely restates FR-001 with additional prose (collision abort, 3-digit guard, SPEC_BASE_PATH). The acceptance criterion is ~150 words of duplicated requirement text | Consolidate AC-12 to reference FR-001 directly: "Given pipeline mode, the validator discovers files per FR-001 rules" |
| F-05 | C | MEDIUM | Plan Todo 3.1 | Extracting shared helpers into `pipelines/lib/speckit-helpers.sh` is a prerequisite for remediation but has no dedicated task in tasks.md — it's mentioned only as context in T029's implementation | Add an explicit task for creating `pipelines/lib/speckit-helpers.sh` (extract `call_llm`, `call_with_retry` from `generate-spec-from-issue.sh`) as a dependency of T029 |
| F-06 | E | MEDIUM | NFR-001 through NFR-006 | Non-functional requirements have no explicit task coverage — NFR-004 (performance <2s for 20 files) has no benchmark test task | Add a task to verify NFR-004 with a parameterized performance test (20 files, assert <2s) |
| F-07 | F | LOW | Plan Phase 5 vs Tasks Phase 8 | Plan calls Phase 5 "Pipeline Integration" while tasks call Phase 8 "Pipeline Integration" — phase numbering drift between plan and tasks makes cross-referencing harder | Align phase numbering or add a mapping note |
| F-08 | B | LOW | Spec NFR-002 | "Concise enough for CI logs" — no measurable criterion for what constitutes acceptable conciseness | Define a maximum line-count target (e.g., "≤3 lines per file + 1 aggregate line") |
| F-09 | D | LOW | Spec | No explicit "Out of Scope" section — constitution-aligned specs typically declare what is NOT included to prevent scope creep | Add a brief Out of Scope section (e.g., "HTML checkbox rendering, non-markdown file types, checklist semantic validation") |
| F-10 | F | LOW | Tasks T031 | T031 references the existing `.gitignore` pattern `specs/*/checklists/.generation-prompt-*.md` and proposes adding a broader `**/checklists/.generation-prompt-*.md` pattern — the task does not verify whether the broader pattern conflicts with or supersedes the narrower one | Add a verification step to T031 confirming the broader pattern subsumes the narrower one, and remove the narrower pattern to avoid redundancy |
| F-11 | C | MEDIUM | Spec FR-001, Plan Todo 2.1 | Pipeline-mode issue number resolution priority includes `issue_key` state key but only "if purely numeric" — no specification of what happens when BOTH `ISSUE_NUMBER` env var AND `--issue-number` CLI arg are absent and `issue_key` is non-numeric (e.g., Jira key). The plan says "skipped" but spec doesn't define final behavior (error? warning? exit 0?) | Specify: if no numeric issue number can be resolved in pipeline mode, exit with error (code 1) and message indicating no issue number found |
| F-12 | G | HIGH | Tasks T008, T009, T010, T011, T012 | Tasks T008–T012 all write tests to the same file `test_count_checkboxes.py` with overlapping scope — they are intentionally granular sub-tasks for one symbol but share identical file path | No action needed — these are intentionally split by test scenario, not duplicative work. Severity HIGH per rules (single file_path dimension match) but low real-world risk |

### Category G Structured Findings

```json
[
  {
    "id": "F-12",
    "overlap_type": "overlapping",
    "severity": "HIGH",
    "task_ids": ["T008", "T009", "T010", "T011", "T012"],
    "dimensions": ["file_path"],
    "rationale": "All five tasks target the same test file tests/unit/cli/speckit/validate_checklists/test_count_checkboxes.py. However, each covers a distinct testing dimension (basic patterns, indentation, backtick fences, tilde fences, nested/edge cases) so descriptions are complementary rather than duplicative. Single-dimension overlap (file_path only) → HIGH per rules."
  }
]
```

## Coverage Summary Table

| Requirement Key | Has Task? | Task IDs | Notes |
|----------------|-----------|----------|-------|
| FR-001 | ✅ | T024, T025, T026, T036 | |
| FR-002 | ✅ | T025, T026, T036 | |
| FR-003 | ✅ | T025 | |
| FR-004 | ✅ | T008, T009, T013 | |
| FR-005 | ✅ | T010, T011, T012, T013 | |
| FR-006 | ✅ | T014, T015 | |
| FR-007 | ✅ | T014, T015 | |
| FR-008 | ✅ | T014, T015 | |
| FR-009 | ✅ | T014, T015 | |
| FR-010 | ✅ | T014, T015 | |
| FR-011 | ✅ | T022, T023, T036 | |
| FR-012 | ✅ | T018, T019 | |
| FR-013 | ✅ | T005, T017, T018, T019, T020, T021 | |
| FR-014 | ✅ | T006, T022, T023 | |
| FR-015 | ✅ | T026, T027 | |
| FR-016 | ✅ | T028, T029 | |
| FR-017 | ✅ | T007, T028, T029, T030 | |
| FR-018 | ✅ | T026, T027 | |
| FR-019 | ✅ | T032, T033, T034, T035 | |
| FR-020 | ✅ | T022, T023, T024, T025 | |
| NFR-001 | ❌ | — | Determinism is implicit in pure-function design but not explicitly tested |
| NFR-002 | ❌ | — | Output conciseness not validated |
| NFR-003 | ✅ | T010, T011, T012, T013 | Covered by fenced-block exclusion tests |
| NFR-004 | ❌ | — | No performance benchmark task |
| NFR-005 | ✅ | T026, T027 | CLI/pipeline use same logic — tested via shared functions |
| NFR-006 | ✅ | T008, T013, T014, T015 | Backward compat implicit in valid-file tests |

## Metrics

| Metric | Value |
|--------|-------|
| Total Requirements | 26 (20 FR + 6 NFR) |
| Total Tasks | 40 |
| Coverage % (FR) | 100% (20/20) |
| Coverage % (all incl. NFR) | 88% (23/26) |
| Ambiguity Count | 3 (F-01, F-02, F-08) |
| Requirement Duplication Count (Category A) | 1 (F-04) |
| Critical Issues Count | 0 |
| Task Deduplication Finding Count | 1 |
| Task Deduplication by Type | duplicate: 0 / overlapping: 1 / conflicting: 0 |
| Multi-Task Group Count | 1 (5 tasks in F-12) |

---
*Generated by Copilot SDK (claude-opus-4.6)*
