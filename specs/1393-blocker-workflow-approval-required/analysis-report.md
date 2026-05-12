# Cross-Artifact Consistency & Quality Analysis Report

**Feature**: Workflow Approval Required Blocks Autonomous AI PR Loop (#1393)
**Artifacts**: spec.md, plan.md, tasks.md, research.md, data-model.md, quickstart.md, contracts/, checklists/
**Primary analysis scope**: spec.md, plan.md, tasks.md
(cross-checked against research.md and data-model.md).
quickstart.md, contracts/, and checklists/ were reviewed
for completeness but not cross-analyzed for consistency findings.
**Date**: 2026-05-12

---

## Findings Table

| ID | Category | Severity | Location(s) | Summary | Recommendation |
| --- | --- | --- | --- | --- | --- |
| F-01 | F | HIGH | FR-004 (spec), Plan §Task 2.1, T006 (tasks) | **Cron schedule contradiction**: Spec FR-004 and Plan Task 2.1 specify `*/2 * * * *` (every 2 minutes); Tasks T006 changes to `*/5 * * * *` with a note about GitHub Actions minimum interval. The three artifacts disagree on a concrete value. | GitHub-hosted scheduled workflows are commonly observed to enforce a minimum interval of approximately 5 minutes, though exact behavior may vary by plan and runner queue depth (see [GitHub Docs: schedule event](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#schedule) for the latest constraints). If the effective minimum is indeed ≥ 5 minutes, align spec FR-004 and Plan §Task 2.1 to `*/5 * * * *` to match T006, and document the platform constraint as the rationale for the change. |
| F-02 | C | MEDIUM | FR-004, FR-007, `.github/ai-pr-loop-config.json` | **Configurable threshold has no configuration surface**: FR-004 describes a "configurable threshold (default: 2 minutes)" but the config schema in FR-007 only defines `trusted_bot_accounts` — no field exists for the threshold value. | Add `approval_threshold_minutes` (or similar) to the config schema in FR-007, or clarify in FR-004 that the threshold is hardcoded with the default value. |
| F-03 | F | MEDIUM | FR-005 (spec example), Plan Task 2.4 | **Audit log schema mismatch**: Spec FR-005 example has 7 fields (`event`, `actor`, `timestamp`, `pr_number`, `run_id`, `source`, `result`). Plan Task 2.4 treats `head_sha` and `reason` as mandatory fields, but those fields are not shown in `spec.md`'s FR-005 example and `spec.md` does not point readers to `data-model.md` for the fuller schema. | Update FR-005 example to include `head_sha` and `reason` fields, or explicitly reference `data-model.md` as the canonical schema source so the spec and plan stay aligned. |
| F-04 | B | MEDIUM | FR-006, T015 | **"Synthetic review event" underspecified**: FR-006 says "posts a synthetic review event" but does not specify the API endpoint (Reviews API vs Issues API), review action type (APPROVE, COMMENT, REQUEST_CHANGES), or body content/format. T015 references `SPECKIT_PR_TOKEN` and a marker pattern but the spec lacks this detail. | Clarify in FR-006 that the synthetic review is a **UX breadcrumb / audit trail** (not a functional approval substitute — it does not satisfy the Actions approval gate). Specify the review action (`COMMENT`) and body format including the `<!-- synthetic-copilot-review -->` marker; the concrete API endpoint can be left as an implementation detail in T015. |
| F-05 | G | HIGH | T002, T003, T017, T018 | **Four tasks modify same file**: All target `.github/workflows/README.md` with different documentation sections (repo settings, PAT scope, monitor docs, pre-check guard). Concurrent authoring risks merge conflicts. | Consolidate into ≤2 documentation tasks (e.g., one for Phase 2 foundational docs, one for Phase 6 polish docs), or add explicit sequential dependencies. |
| F-06 | G | CRITICAL | T008, T029 | **API query strategy overlap**: T008 implements run listing/filtering in `workflow-approval-monitor.yml`; T029 validates the same query strategy against a real run and may change the implementation. Both target the same file with closely related intent. | Merge T029 into T008 as a validation sub-step, or reframe T029 as a manual verification item in T022's checklist. |
| F-07 | F | MEDIUM | NFR-001, FR-004, T006 | **SLA vs polling latency mismatch**: NFR-001 requires approval "within 60 seconds of detection," but detection depends on the polling interval (2–5 minutes per F-01). Total worst-case latency from `action_required` to approval could be 6+ minutes, not 60 seconds. | Clarify in NFR-001 that the 60-second SLA starts from the monitor's detection (poll hit), not from when the run first enters `action_required`. Document total worst-case end-to-end latency. |
| F-08 | C | MEDIUM | US1 acceptance scenarios, T005 | **US1 acceptance has no verification task**: US1 requires lint workflow to execute without approval for trusted bots. T005 (the only US1 implementation task) only adds inline comments — no task validates that the repo settings change (FR-001/FR-002) actually unblocked bot PRs. | Add explicit verification of bot PR unblocking to T022's manual checklist, or create a dedicated smoke-test task. |
| F-09 | B | LOW | Plan §2 (Research Summary), Plan §Task 2.4 | **Document references resolved**: Plan references `research.md` and `data-model.md` as linked companion documents; both are now included in the spec directory alongside the plan. | No action required — referenced documents are present. |

---

### Category G Structured Findings

> **Machine-readable export** — The raw JSON array below is the structured
> representation of the Category G findings for downstream tooling consumption.
> It mirrors the corresponding rows in the Findings Table above.

[
  {
    "id": "F-05",
    "overlap_type": "overlapping",
    "severity": "HIGH",
    "task_ids": ["T002", "T003", "T017", "T018"],
    "dimensions": ["file_path"],
    "rationale": "All four tasks edit `.github/workflows/README.md` in overlapping sections. Parallel edits can conflict; consolidate into fewer tasks or enforce explicit sequencing."
  },
  {
    "id": "F-06",
    "overlap_type": "overlapping",
    "severity": "CRITICAL",
    "task_ids": ["T008", "T029"],
    "dimensions": ["description", "file_path"],
    "rationale": "T008 implements query listing/filtering in `workflow-approval-monitor.yml`, while T029 validates and may revise the same logic. Merge them or make T029 a validation sub-step."
  }
]

---

## Implementation Coverage Summary Table

| Requirement Key | Has Implementation Task? | Implementation Task IDs | Notes |
| --- | --- | --- | --- |
| FR-001 | ✅ | T002, T005 | Documented via repo settings; T005 adds comments only |
| FR-002 | ✅ | T002 | Documentation of policy setting |
| FR-003 | ✅ | T003, T011, T028 | PAT scope docs + approve API call + PAT validation update |
| FR-004 | ✅ | T008 | Run listing with threshold filtering |
| FR-005 | ✅ | T012 | Structured audit logging |
| FR-006 | ✅ | T015, T016 | Synthetic review fallback + breadcrumb logging |
| FR-007 | ✅ | T001, T007, T009 | Config file creation + loading + author filtering |
| FR-008 | ✅ | T010 | Idempotency guard |
| FR-009 | ✅ | T004 | Dispatch pre-check guard |
| NFR-001 | ⚠️ | — | No explicit test; partially addressed by T011. See [NFR Test Coverage Summary](#nfr-test-coverage-summary) for testable criterion and details. |
| NFR-002 | ✅ | T005 | Documented via inline comments; no changes to lint workflow |
| NFR-003 | ✅ | T003, T011 | Token docs + implementation uses existing secret |
| NFR-004 | ✅ | T009, T020 | Fork check in monitor + test for rejection |
| NFR-005 | ✅ | T012, T025 | Audit logging implementation + test |
| NFR-006 | ✅ | T013, T014 | Retry tracking + failure notification |

### FR Test Coverage Summary (Functional Requirements Only)

| FR | Priority | User Story | Test Task IDs | Test Types | Status |
| --- | --- | --- | --- | --- | --- |
| FR-001 | P1 | US1 | T020 | unit, happy-path | ✅ Covered |
| FR-002 | P1 | US1 | T020 | unit, happy-path | ✅ Covered |
| FR-003 | P2 | US2 | T023 | unit, happy-path | ✅ Covered |
| FR-004 | P2 | US2 | T024 | unit | ✅ Covered |
| FR-005 | P2 | US2 | T025 | unit, happy-path | ✅ Covered |
| FR-006 | P3 | US3 | T026 | unit | ✅ Covered |
| FR-007 | P2 | US2 | T019, T020 | unit, happy-path | ✅ Covered |
| FR-008 | P2 | US2 | T021 | unit | ✅ Covered |
| FR-009 | P1 | US4 | T027 | unit, happy-path | ✅ Covered |

### NFR Test Coverage Summary

> NFR coverage is tracked separately from functional requirements. NFR-001 is
> currently uncovered by explicit tests (see finding F-07 for latency SLA
> clarification needs).

| NFR | Priority | Test Task IDs | Test Types | Status |
| --- | --- | --- | --- | --- |
| NFR-001 | ⚠️ | — | — | ⚠️ No explicit test; partially addressed by implementation timing in T011. **Testable criterion**: detection = the UTC timestamp when the monitor poll first observes `action_required` status on the workflow run; approval = the UTC timestamp when the GitHub API returns a 2xx response to the approval request; SLA = approval\_ts − detection\_ts ≤ 60 s (see spec NFR-001 and finding F-07). |
| NFR-002 | P2 | T005 | documentation | ✅ Covered (inline comments; no lint workflow changes) |
| NFR-003 | P2 | T003, T011 | documentation, implementation | ✅ Covered (token docs + existing secret reuse) |
| NFR-004 | P2 | T009, T020 | unit | ✅ Covered (fork check in monitor + rejection test) |
| NFR-005 | P2 | T012, T025 | unit | ✅ Covered (audit logging implementation + test) |
| NFR-006 | P2 | T013, T014 | unit | ✅ Covered (retry tracking + failure notification) |

---

## Metrics

| Metric | Value |
| --- | --- |
| Total Requirements (FR + NFR) | 15 |
| Total Tasks | 29 |
| FR Coverage % | 100% (9/9) |
| Ambiguity Count (Category B) | 1 (F-04 unresolved; F-09 resolved — excluded from count) |
| Requirement Duplication Count (Category A) | 0 |
| Critical Issues Count | 1 (CRITICAL severity: F-06) |
| High Issues Count | 2 (HIGH severity: F-01, F-05) |
| Task Deduplication Finding Count | 2 |
| Task Deduplication by Type | 0 duplicate / 2 overlapping / 0 conflicting |
| Multi-Task Group Count | 1 (F-05: 4 tasks) |

---
*Generated by Copilot SDK (claude-opus-4.6)*
