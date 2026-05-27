# Cross-Artifact Consistency and Quality Analysis

## Findings Table

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| F-01 | F | MEDIUM | Spec FR-001 vs Plan Phase 2 | Spec says fallback logic is a "dedicated workflow step" using `actions/github-script` block, but Plan Phase 2 creates a JavaScript module at `.github/scripts/speckit-trigger/agent-fallback.js`. The plan's architecture decision section explains the rationale, but the spec's Clarifications section still says "composite action (or `actions/github-script` block)" introducing ambiguity about the component type. | Align spec clarification text to definitively state "reusable JavaScript module invoked via `actions/github-script`" matching the plan's architecture decision. |
| F-02 | B | LOW | Spec FR-001 | "any other structural validators defined in the SpecKit pipeline" is open-ended. Plan Phase 2 enumerates 8 signatures (`STRUCTURAL_ERROR_SIGNATURES`), but spec doesn't fully enumerate them. | Enumerate all 8 known signatures in FR-001 or reference the constant definition location explicitly. |
| F-03 | F | MEDIUM | Spec FR-001 vs Codebase | Spec says orchestrator step "MUST emit signatures via `$GITHUB_OUTPUT`" but current `generate-spec-from-issue.sh` does not emit `validation_errors` output — only `markdownlint_status`, `clarify_status`, etc. T004 addresses this but this is a net-new modification, not leveraging an existing mechanism. | No action needed (T004 covers this). Flag as implementation risk: the script is ~3800 lines and modifications require careful placement. |
| F-04 | C | MEDIUM | Spec NFR-001 | "The agent fallback step MUST complete within 30 seconds" but no specification of what constitutes the timeout boundary — does this include idempotency checks and label operations, or only the API call? | Clarify that the 30s budget includes all sub-operations (detection + idempotency + API call + label/comment). Task T049 addresses this but should specify `timeout-minutes: 1` (GitHub Actions minimum granularity is 1 minute). |
| F-05 | F | LOW | Plan Phase 1 vs Tasks T004/T005 | Plan says "Modify `generate-spec-from-issue.sh` to write `validation_errors` to `$GITHUB_OUTPUT` when structural validation fails (specify phase and clarify phase)" — explicitly mentions both specify and clarify phases. Tasks T004/T005 don't specify which internal code paths (specify vs clarify) need modification. | Add clarifying note to T004/T005 that both the specify retry loop and clarify retry loop failure paths need signal emission. |
| F-06 | G | HIGH | T021, T037, T038, T039 | T021 (Phase 3) tests graceful degradation for non-2xx, missing fields, and timeout. T037/T038/T039 (Phase 6) test the same three scenarios individually. Overlapping test scope with same assertions. | Clarify that T021 covers the `triggerCodingAgent()` unit boundary while T037–T039 test the end-to-end label+comment outcome. Consider merging T037–T039 into T021 or explicitly differentiating scope. |
| F-07 | G | HIGH | T022, T040, T041 | T022 implements graceful degradation in `triggerCodingAgent()` setting `outputs.triggered = 'false'`. T040 implements "enhanced failure comment template" and T041 ensures `outputs.triggered = 'false'` on degradation paths. T041 is a subset of T022's implementation. | Merge T041 into T022 or redefine T041 as a verification/review task rather than an implementation task. |
| F-08 | E | MEDIUM | NFR-002 | NFR-002 (maintainability of error signatures) has no dedicated task. T012 partially covers it by defining `STRUCTURAL_ERROR_SIGNATURES` constants, but no task validates co-location documentation or cross-references to `spec-validation.sh`. | Add a sub-task or acceptance criterion to T012 ensuring the constants reference the source definitions in `spec-validation.sh`. |
| F-09 | E | MEDIUM | NFR-003 | NFR-003 (no new secrets) has no dedicated task or verification step. It's implicitly satisfied by using `COPILOT_GITHUB_TOKEN` but no task verifies this constraint. | Add a checklist item to T047 or T050 to explicitly verify no new secrets are introduced. |
| F-10 | E | MEDIUM | NFR-004 | NFR-004 (48KB truncation) is covered by T014 implementation but has no dedicated test verifying the byte-level boundary (49,152 bytes including marker). T008 tests truncation but the description says "verify truncation to 49,152 bytes" without specifying boundary precision. | Ensure T008 explicitly tests the exact boundary: 49,151 bytes (no truncation) vs 49,153 bytes (truncated with marker fitting within budget). |
| F-11 | C | LOW | Spec Edge Cases | "Issue body exceeds 48KB" edge case specifies 49,152 bytes but doesn't define whether this applies to the raw GitHub API response body or the rendered markdown content. | Clarify that the 48KB limit applies to the UTF-8 encoded raw issue body string as retrieved from the GitHub Issues API. |
| F-12 | F | LOW | Tasks T007–T011 vs Codebase | Tasks reference "existing `speckit-trigger` test harness" for shell-based tests, but the plan's architecture decision chose JavaScript (`agent-fallback.js`). Shell-based tests would test a JavaScript module indirectly. | Clarify whether T007–T011 are shell integration tests that invoke the workflow step, or JavaScript unit tests (e.g., Jest/Vitest) for `agent-fallback.js`. The test file naming convention (`.sh`) suggests shell tests testing the overall step behavior. |

### Category G Structured Findings

[{"id": "G-01", "overlap_type": "overlapping", "severity": "HIGH", "task_ids": ["T021", "T037", "T038", "T039"], "dimensions": ["description"], "rationale": "T021 tests graceful degradation for non-2xx, missing fields, and network timeout in triggerCodingAgent(). T037/T038/T039 individually test the same three degradation scenarios (API 500/503, network timeout, malformed response). Single-dimension overlap on description — same failure modes tested at different abstraction levels (unit vs integration outcome)."}, {"id": "G-02", "overlap_type": "overlapping", "severity": "HIGH", "task_ids": ["T022", "T041"], "dimensions": ["description"], "rationale": "T022 implements graceful degradation in triggerCodingAgent() setting outputs.triggered='false' on failures. T041 ensures outputs.triggered is set to 'false' on all degradation paths — this is a strict subset of T022's implementation scope. Same outcome, same code location, but T041 could be interpreted as a cross-cutting verification across all paths rather than just the API function."}]

## Coverage Summary Table

| Requirement Key | Has Task? | Task IDs | Notes |
|----------------|-----------|----------|-------|
| FR-001 | ✅ | T004, T005, T007, T012, T013 | Well covered |
| FR-002 | ✅ | T004, T007, T012, T013 | Well covered |
| FR-003 | ✅ | T008, T014 | Covered |
| FR-004 | ✅ | T009, T015 | Covered |
| FR-005 | ✅ | T023, T026 | Covered |
| FR-006 | ✅ | T024, T026 | Covered |
| FR-007 | ✅ | T023, T026 | Covered |
| FR-008 | ✅ | T031, T034, T036 | Covered |
| FR-009 | ✅ | T010, T016, T043 | Covered |
| FR-010 | ✅ | T011, T017, T018, T019 | Covered |
| FR-011 | ✅ | T021, T022, T037–T041, T046 | Heavily covered (potential over-testing) |
| FR-012 | ✅ | T025, T027, T028, T029, T030 | Covered |
| FR-013 | ✅ | T032, T035, T036 | Covered |
| NFR-001 | ✅ | T049 | Covered |
| NFR-002 | ⚠️ | T012 (partial) | No dedicated verification task |
| NFR-003 | ⚠️ | — | Implicitly satisfied, no verification task |
| NFR-004 | ✅ | T008, T014 | Covered |
| NFR-005 | ✅ | T047, T048 | Covered |

## Metrics

| Metric | Value |
|--------|-------|
| Total Requirements | 18 (13 FR + 5 NFR) |
| Total Tasks | 51 |
| Coverage % | 89% (16/18 have dedicated tasks) |
| Ambiguity Count | 1 |
| Requirement Duplication Count (Category A) | 0 |
| Critical Issues Count | 0 |
| Task Deduplication Finding Count | 2 |
| Task Deduplication by Type | duplicate: 0 / overlapping: 2 / conflicting: 0 |
| Multi-Task Group Count | 1 (G-01 involves 4 tasks) |

---

## Next Actions

1. Align the spec wording for FR-001 with the plan's chosen implementation approach (`actions/github-script` invoking a reusable JavaScript module).
2. Clarify open specification details called out above, especially timeout scope, structural validator signatures, and exact failure-path/output requirements.
3. De-duplicate or re-scope overlapping implementation and test tasks to reduce redundant work before execution.

Would you like me to suggest concrete remediation edits for the spec, plan, and tasks to resolve the findings above?

*Generated by Copilot SDK (claude-opus-4.6)*
