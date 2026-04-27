# Analysis Report: SpecKit FR Validation Gate (#1199)

## Findings Table

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| F-01 | Duplication | MEDIUM | Spec FR-002, FR-003 | FR-002 and FR-003 both specify case-insensitive word-boundary matching for coverage checks. FR-003 largely restates FR-002's matching semantics with minor rewording. | Consolidate FR-003 into FR-002 or make FR-003 solely about the "covered" definition (≥1 match) without restating matching rules. |
| F-02 | Underspecification | HIGH | Spec FR-012, Plan Exit Codes, Tasks T014/T030 | FR-012 specifies only exit code 0 (covered) and "non-zero" (uncovered). The plan introduces exit code 2 for operational errors (T014, T030), which is a new requirement not in the spec. Pipeline logic depends on distinguishing exit codes 1 vs 2. | Add exit code 2 to FR-012 explicitly: 0 = pass, 1 = uncovered FRs, 2 = operational error. |
| F-03 | Inconsistency | MEDIUM | Spec FR-008, Plan Phase 1/3 | FR-008 says `--max-retries` is on the CLI command, implying the CLI retries. Plan clarifies the CLI is single-pass and bash does retries. The CLI flag exists only for metadata/forwarding. This contradicts the natural reading of FR-008. | Reword FR-008 to clarify the CLI flag reports/validates the retry budget but does not internally retry. Add "The retry loop is implemented in the pipeline bash script." |
| F-04 | Coverage Gap | MEDIUM | Spec NFR-001 | NFR-001 requires validation under 1 second for 100KB input. No task benchmarks or tests performance. | Add a performance test or assertion in T037/T038, or add a dedicated task for a simple timing assertion. |
| F-05 | Coverage Gap | LOW | Spec NFR-004 | NFR-004 requires output consistent with existing SpecKit conventions (structured logging, exit codes). No task explicitly validates output format consistency with other `agdt-speckit-*` commands. | Add a review checkpoint in T031 or T038 to verify output format matches existing SpecKit command conventions. |
| F-06 | Inconsistency | MEDIUM | Plan Phase 3, Pipeline | Plan references `speckit-phase-progression.yml` as an internal dependency but no task updates it. T020/T021 modify `generate-spec-from-issue.sh` but the workflow YAML may need condition updates for the new validation step. | Add a task to review/update `speckit-phase-progression.yml` if the new bash function changes phase exit behavior, or explicitly document why no change is needed. |
| F-07 | Ambiguity | MEDIUM | Spec FR-007, Tasks T024/T025 | FR-007 says "re-invoke task generation with a prompt that explicitly lists the uncovered FR identifiers" but does not specify the prompt format or how uncovered FRs are injected (env var, stdin, appended to existing prompt, separate file). | Specify the retry prompt mechanism: e.g., "append uncovered FR list to the tasks agent prompt as a structured section." |
| F-08 | Underspecification | LOW | Spec FR-013, Tasks T032-T034 | FR-013 says the analysis report "MUST include a deterministic FR coverage section" but does not define the section format, heading name, or placement within the report. The plan uses `fr-coverage.json` as an intermediate file but this is not in the spec. | Add `fr-coverage.json` as an intermediate artifact to the spec, and specify the expected section heading (e.g., "## FR Coverage") in the analysis report. |
| F-09 | Inconsistency | LOW | Plan §2 Research, Pipeline | Plan says insertion point is "between `run_tasks_phase` and `run_analyze_phase`" but in single-phase mode (phase 4), there is no `run_analyze_phase` call — phase 4 ends after tasks + markdownlint. T020 says "before the script exits" which is correct, but this contradicts the plan's generic phrasing. | Clarify in plan that single-phase mode inserts validation before markdownlint/exit, not before `run_analyze_phase`. |
| F-10 | Coverage Gap | LOW | Spec SM4 | SM4 requires "100% unit test coverage for the validation module." No task explicitly runs `agdt-test-file --source-file agentic_devtools/cli/speckit/validate_frs.py` for targeted 100% coverage verification. T037 runs full suite. | Add explicit `agdt-test-file --source-file agentic_devtools/cli/speckit/validate_frs.py` step to ensure 100% coverage for the new module specifically. |
| F-11 | Underspecification | LOW | Spec US3, FR-010 | FR-010/US3 don't specify behavior when `--spec-file` or `--tasks-file` paths don't exist. EC3/EC4 cover empty files but not missing paths. The plan mentions "missing `spec.md`" in exit code discussion but the spec only says "empty or missing" in edge cases. | Clarify in FR-010 or EC3/EC4: when a specified path does not exist, treat as empty file (EC3/EC4 behavior applies). |
| F-12 | Inconsistency | LOW | Tasks T020 | T020 says "immediately after `run_tasks_phase`, before `markdownlint` runs / before the script exits" for single-phase path. Actual code in `scripts/generate-spec-from-issue.sh` (lines 2371-2379) shows tasks phase → markdownlint. The `/` phrasing is ambiguous about whether validation goes before or after markdownlint. | Clarify T020: validation should run after `run_tasks_phase` and before markdownlint validation. |

## Coverage Summary Table

| Requirement Key | Has Task? | Task IDs | Notes |
|----------------|-----------|----------|-------|
| FR-001 | ✅ | T004, T008 | Extraction regex + dedup |
| FR-002 | ✅ | T005, T009 | Case-insensitive word-boundary coverage check |
| FR-003 | ✅ | T005, T009 | Overlaps with FR-002 (see F-01) |
| FR-004 | ✅ | T013, T014, T031 | Report uncovered FRs in CLI output |
| FR-005 | ✅ | T020, T021 | Block PR creation via exit code |
| FR-006 | ✅ | T020, T021 | Pipeline ordering after tasks, before PR |
| FR-007 | ✅ | T024, T025 | Retry with uncovered FR feedback |
| FR-008 | ✅ | T014, T022, T023, T029 | Max retries with precedence |
| FR-009 | ✅ | T024, T025 | Re-validation after retry |
| FR-010 | ✅ | T014 | CLI --spec-file and --tasks-file |
| FR-011 | ✅ | T014, T028 | JSON output schema and sort order |
| FR-012 | ✅ | T013, T014 | Exit codes (spec says 0/non-zero; plan adds code 2 — see F-02) |
| FR-013 | ✅ | T032, T033, T034 | Analysis report enrichment |
| FR-014 | ✅ | T012, T030 | No FRs → warning + pass |
| NFR-001 | ❌ | — | No performance test task (see F-04) |
| NFR-002 | ✅ | T008, T009, T010 | Deterministic by design (no LLM calls) |
| NFR-003 | ✅ | T008, T009, T012 | Read-only by design |
| NFR-004 | ❌ | — | No explicit format consistency check (see F-05) |
| NFR-005 | ✅ | T028 | Deterministic output tested via sort order |
| EC1 | ✅ | T004, T008 | Case-insensitive dedup |
| EC2 | ✅ | T005 | Code block coverage |
| EC3 | ✅ | T030 | Empty/missing tasks.md |
| EC4 | ✅ | T030 | Empty/missing spec.md |
| EC5 | ✅ | T004, T008 | Varying digit counts |

## Metrics

| Metric | Value |
|--------|-------|
| Total Functional Requirements | 14 |
| Total Non-Functional Requirements | 5 |
| Total Tasks | 38 |
| FR Coverage % | **100%** (14/14) |
| NFR Coverage % | **60%** (3/5 with explicit tasks) |
| Ambiguity Count | 1 (F-07) |
| Duplication Count | 1 (F-01) |
| Critical Issues Count | **0** |
| High Issues Count | 1 (F-02) |
| Medium Issues Count | 4 (F-03, F-04, F-06, F-07) |
| Low Issues Count | 6 (F-05, F-08, F-09, F-10, F-11, F-12) |
| Total Findings | 12 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
