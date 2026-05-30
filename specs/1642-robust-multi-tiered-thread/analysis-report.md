# Cross-Artifact Consistency & Quality Analysis Report

## Findings Table

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| F-01 | F | MEDIUM | Plan Phase 3 / Tasks T014 | Plan mentions expanding query in both `github_provider.py` and `resolve_review_threads.py`, but tasks only reference `github_provider.py` for the query expansion. The CLI command file `resolve_review_threads.py` query update is not explicitly tasked. | Add a task to update `_REVIEW_THREADS_QUERY` in `cli/github/resolve_review_threads.py` or clarify in T014 that both locations are covered. |
| F-02 | G | HIGH | T033, T035 | T033 tests `TieredResolutionEngine` (tier ordering, short-circuit, TENTATIVE, batch processing) and T035 tests mock provider driving the full resolution pipeline through `TieredResolutionEngine` — both in `tests/unit/cli/ci/resolution/engine/`. T035 is a superset validation but overlaps T033's engine exercise. | Accept as intentional layering (platform-agnostic validation vs unit tests). Single-dimension overlap only. |
| F-03 | F | MEDIUM | Tasks T003 vs actual task IDs in E.2 data | E.2 test coverage JSON references task IDs (T049, T051, T052, T053, T057, T058, T060, T064, T065) that do not exist in the task list (max is T046). Task list and coverage data are out of sync. | Regenerate E.2 coverage data against the current task list, or add the missing tasks (T047–T065) to tasks.md. |
| F-04 | C | MEDIUM | FR-003, Spec | FR-003 defines "originating review commit OID" per-thread via `commit_id` field on the review, but the GraphQL query expansion (T014) fetches `commit { oid }` from comment nodes, not from the review object. The spec/plan don't clarify which GraphQL field maps to the "review commit_id". | Clarify whether the originating review commit is from the `PullRequestReview.commit` field or from the first comment's `commit { oid }` field in the query design. |
| F-05 | B | MEDIUM | NFR-002, SC-001 | NFR-002 says "at least 40% reduction in SDK invocations"; SC-001 says "programmatic tiers resolve at least 50% of threads previously resolved only via SDK". These are related but distinct metrics with no task explicitly measuring/validating either post-deployment. | Add a validation task or acceptance test that instruments SDK call counts and programmatic resolution rates. |
| F-06 | C | MEDIUM | FR-009, Tasks T025 | FR-009 specifies the fallback agent uses `default-thread-resolution-fallback-prompt.md` loaded "via direct path read rather than `load_prompt_template()`" (plan Phase 7). No task explicitly tests this loading mechanism vs the standard template loader. | Add a test case in T024/T025 verifying the prompt is loaded via direct file read, not the workflow-scoped loader. |
| F-07 | F | MEDIUM | Spec US5/FR-008 vs Plan Phase 7 | Spec FR-008 defines `AMBIGUOUS` as a valid SDK verdict token that "triggers the retry/fallback path". Plan Phase 7 says retry fires on "malformed response". An `AMBIGUOUS` verdict is well-formed but triggers retry — plan should distinguish malformed-format vs ambiguous-verdict retry paths. | Clarify in T023/T025 that retry fires on BOTH malformed format AND `AMBIGUOUS` verdict, as two distinct code paths. |
| F-08 | D | LOW | Spec | No explicit "Out of Scope" section listing deferred features (e.g., configurable markers from `.github/agdt-config.json`, Azure DevOps provider implementation). Clarifications mention these but they're scattered. | Add a formal "Out of Scope" section consolidating deferred items for Phase 1. |
| F-09 | E | MEDIUM | NFR-001, NFR-004, Tasks | NFR-001 (500ms/45s timing) has T042; NFR-004 (rate limiting) has T043. But NFR-002 (40% SDK reduction measurement) and NFR-005 (human-readable replies) have no dedicated validation tasks. | Add acceptance/validation tasks for NFR-002 and NFR-005 or map them to existing tasks explicitly. |
| F-10 | B | LOW | NFR-001 | "500 milliseconds per thread" for programmatic tiers — no clarity on whether this is p50, p95, p99, or hard ceiling. | Specify the percentile or clarify as a hard ceiling (timeout/abort). |
| F-11 | F | MEDIUM | Task dependency graph | Dependency graph states "T040 → T041–T046 (integration before polish)" but T040 is part of Phase 13 (Integration) alongside T037–T039. T041–T046 depend on T040 completing, but T037–T039 are peers of T040, creating circular-looking dependency. | Restate as "T037–T040 → T041–T046" to clarify all integration tasks precede polish. |

## Coverage Summary Table

| Requirement Key | Has Task? | Task IDs | Notes |
|----------------|-----------|----------|-------|
| FR-001 | ✅ | T033, T034 | Engine orchestration enforces tier ordering |
| FR-002 | ✅ | T009, T010 | Precondition removal |
| FR-003 | ✅ | T011, T012, T014 | Per-thread commit check + expanded query |
| FR-004 | ✅ | T013, T014 | GraphQL query expansion |
| FR-005 | ✅ | T017, T018 | isOutdated tier |
| FR-006 | ✅ | T019, T020 | Automation markers tier |
| FR-007 | ✅ | T021, T022 | Diff heuristic tier |
| FR-008 | ✅ | T023, T025 | Structured VERDICT parsing |
| FR-009 | ✅ | T024, T025, T026 | Retry + fallback agent |
| FR-010 | ✅ | T029, T030, T031, T032, T033, T034 | Tentative resolution |
| FR-011 | ✅ | T027, T028 | Structured reply |
| FR-012 | ✅ | T027, T028 | HTML markers |
| FR-013 | ✅ | T005, T006, T035, T036 | Platform-agnostic protocols |
| FR-014 | ✅ | T029, T030, T031, T032 | Tentative re-evaluation |
| FR-015 | ✅ | T029, T030 | Per-thread state persistence |
| NFR-001 | ✅ | T042 | Timing instrumentation |
| NFR-002 | ⚠️ | — | No explicit measurement/validation task |
| NFR-003 | ✅ | T041 | DEBUG logging |
| NFR-004 | ✅ | T043 | Rate limit backoff |
| NFR-005 | ⚠️ | — | Implicit in T028 but no dedicated validation |
| NFR-006 | ✅ | T005, T006 | Protocol classes |

## Metrics

| Metric | Value |
|--------|-------|
| Total Requirements | 21 (15 FR + 6 NFR) |
| Total Tasks | 46 |
| Coverage % | 90% (19/21 have explicit tasks) |
| Ambiguity Count | 2 (F-05, F-10) |
| Requirement Duplication Count (Category A) | 0 |
| Critical Issues Count | 0 |
| Task Deduplication Finding Count | 0 |
| Task Deduplication by Type | duplicate: 0 / overlapping: 0 / conflicting: 0 |
| Multi-Task Group Count | 0 |

### Category G Structured Findings

[]

## Next Actions

No CRITICAL issues were found — you may proceed with `/speckit.agdt:implement`. The following improvements are recommended before or alongside implementation:

1. **F-01 / F-03 (MEDIUM — task gaps):** Add a task for updating `_REVIEW_THREADS_QUERY` in `resolve_review_threads.py`, and regenerate E.2 coverage data
   against the current 46-task list to eliminate the T047–T065 phantom references.
2. **F-07 (MEDIUM — ambiguous retry logic):** Clarify in T023/T025 that retry fires on both malformed format _and_ `AMBIGUOUS` verdict as distinct code paths.
   Run `/speckit.agdt:specify` with a targeted refinement to FR-008 if needed.
3. **F-09 (MEDIUM — NFR coverage gaps):** Add explicit validation tasks for NFR-002 (40% SDK reduction measurement) and NFR-005 (human-readable reply quality).
   Manually edit `tasks.md` to map these requirements to new tasks or annotate existing tasks.
4. **F-11 (MEDIUM — dependency graph):** Restate the dependency graph entry as "T037–T040 → T041–T046" to eliminate the apparent circular dependency. Manually edit `tasks.md`.
5. **F-05 / F-04 (MEDIUM — spec/plan ambiguity):** Add a note to the spec clarifying the GraphQL field for originating review commit OID, and add an acceptance test measuring SDK call reduction.

Would you like me to suggest concrete remediation edits for the top issues (F-01, F-03, F-07, F-09, F-11)?

---
_Generated by Copilot SDK (claude-opus-4.6)_
