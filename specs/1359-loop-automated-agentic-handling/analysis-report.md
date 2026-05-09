# Cross-Artifact Consistency & Quality Analysis Report

**Feature**: AI PR Loop Automated Agentic Repair (#1359)
**Artifacts**: spec.md, plan.md, tasks.md
**Analysis Date**: 2026-05-09

---

## Findings Table

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| A-01 | Duplication | LOW | FR-010, SEC-006 | Both require skipping dispatch for PRs modifying privileged paths. Spec acknowledges overlap ("already covered by FR-010"). | Consolidate SEC-006 as a cross-reference to FR-010 |
| A-02 | Duplication | LOW | FR-013, SEC-001 | Both require skipping dispatch for fork PRs. Spec acknowledges overlap. | Consolidate SEC-001 as a cross-reference to FR-013 |
| A-03 | Duplication | LOW | NFR-001, FR-012 | NFR-001 restates FR-012's 15-minute timeout with identical enforcement mechanism (`timeout-minutes: 15`). | Merge NFR-001 into FR-012 or make NFR-001 reference FR-012 |
| B-01 | Ambiguity | MEDIUM | NFR-004 | "retry with backoff where appropriate" lacks measurable criteria — no retry count, backoff strategy, or max wait. | Specify: e.g., 3 retries, exponential backoff starting at 2s, max 30s |
| B-02 | Ambiguity | MEDIUM | SEC-007, Plan §3.9 | Secret-scanning grep pattern `(token\|password\|secret\|api_key\|private_key)` is overly broad — matches `token_count`, `secret_key_rotation_policy`, etc. No false-positive suppression. | Use purpose-built scanner (e.g., `gitleaks`) or document accepted false-positive risk with allowlist |
| B-03 | Ambiguity | LOW | SC-001, SC-002, SC-003 | Success criteria percentages (≥80%, ≥90%) and median time (<10 min) lack measurement methodology, sample size, and observation window. | Add measurement window (e.g., 30-day rolling), minimum sample size, and tooling |
| C-01 | Underspecification | MEDIUM | SEC-002 | PAT permissions well-defined but no token rotation/expiry policy, no creation responsibility, no revocation procedure for departing token owners. | Add token lifecycle section: creation, max expiry, rotation cadence, revocation |
| C-02 | Underspecification | MEDIUM | FR-002 | "Required checks" referenced but never explicitly defined as GitHub branch protection required status checks. | Add: "required checks as configured in the repository's branch protection rules" |
| C-03 | Underspecification | MEDIUM | Edge Cases (spec) | Merge conflict detection stated as expected behavior ("detect and report") but no mechanism specified. Plan Phase 3 Task 4 also underspecified. | Specify detection: e.g., `gh pr view --json mergeable` field check |
| C-04 | Underspecification | MEDIUM | Plan §3.3 Task 7 | `start_copilot_session()` return type handling assumes `CopilotSessionResult.process` is `None` only when fallback occurs, but no documentation of when `.process` could be `None` for other reasons (e.g., binary found but failed to launch). | Document all `.process == None` scenarios in the session launcher or add explicit error classification |
| E-01 | Coverage Gap | MEDIUM | NFR-004 | No task implements API retry-with-backoff for `gh api`/`github.rest.*` calls. Previously mapped tasks T029 (dedup guard verification) and T030 (timeout verification) address unrelated concerns. | Add task for retry-with-backoff wrapper on workflow `gh api` calls |
| E-02 | Coverage Gap | MEDIUM | SEC-002 | T012/T053 validate PAT *presence* (masking + fail-fast on empty) but no task validates PAT *permission scoping* at runtime. Insufficient permissions would produce opaque failures. | Add a PAT permission smoke test task (e.g., attempt a read-only API call and validate the response) |
| F-01 | Inconsistency | MEDIUM | FR-007 (spec) vs Plan §1.2 | FR-007 implies posting a *new* "human intervention required" comment when 3-dispatch limit reached. Plan consolidates into PATCH on existing marker. Spec not updated to match. | Update FR-007 to reflect the consolidated-comment design |
| F-02 | Inconsistency | HIGH | FR-005 (spec) vs Plan §3.3 | Spec FR-005 says session launcher "falls back to `gh copilot suggest`." Plan Phase 3 Task 3 states `gh copilot suggest` lacks `--allow-all`/`--autopilot` needed for autonomous execution — the fallback is non-functional for the repair job. | Update FR-005 to document standalone binary requirement and note `gh copilot suggest` fallback is insufficient for CI repair |
| F-03 | Inconsistency | MEDIUM | Spec Key Entities vs Plan §1.2 | Spec's "Deduplication Guard" entity carries only dispatch count/format. Plan and tasks consolidate repair status (pending/started/completed/failed) into the same comment. Entity definition incomplete. | Update Deduplication Guard entity to include status tracking fields |
| F-04 | Inconsistency | MEDIUM | Plan §3.3 Task 3 vs FR-005 | Plan introduces `AGDT_VERSION` env variable pinned to `0.42.0` but no task or spec requirement mandates a version bump process when new features are needed by the repair job. | Add guidance for when/how to bump `AGDT_VERSION` after new releases |
| G-01 | Task Dedup | LOW | T034, T061 | T034 (CI failure dispatch detection) and T061 (dedup guard happy-path verification) have distinct scopes despite shared phase — not duplicates. | No action needed |
| G-02 | Task Dedup | MEDIUM | T031, T046 | T046 (manual timeout test) and T031 (CI log retrieval) share structured metadata concerns. Potential consolidation during implementation. | Review overlap during implementation; consider folding T046 acceptance criteria into T031 |

---

## Coverage Summary Table

| Requirement Key | Has Task? | Task IDs | Notes |
|----------------|-----------|----------|-------|
| FR-001 | ✅ | T002, T007, T048, T050, T051 | |
| FR-002 | ✅ | T031, T032, T034, T049, T050, T057 | |
| FR-003 | ✅ | T011, T052 | |
| FR-004 | ✅ | T012, T053 | |
| FR-005 | ✅ | T013, T017, T019, T059 | See F-02: spec/plan inconsistency on fallback |
| FR-006 | ✅ | T027, T028, T060 | |
| FR-007 | ✅ | T003, T029, T043, T061 | |
| FR-008 | ✅ | T023, T025, T054 | |
| FR-009 | ✅ | T007, T026, T048, T055 | |
| FR-010 | ✅ | T002, T004, T044 | |
| FR-011 | ✅ | T006, T056 | |
| FR-012 | ✅ | T011, T030, T046, T062 | |
| FR-013 | ✅ | T002, T045 | |
| FR-014 | ✅ | T002, T058 | |
| FR-015 | ✅ | T047, T050 | |
| NFR-001 | ✅ | (via FR-012) | Duplicate of FR-012 (A-03) |
| NFR-002 | ✅ | T047 | |
| NFR-003 | ✅ | T012, T017 | T012 adds `::add-mask::` (NFR-003) |
| NFR-004 | ⚠️ | — | No task implements API retry-with-backoff; T029 (dedup guard) and T030 (timeout) were incorrectly mapped here (E-01) |
| NFR-005 | ✅ | T062 | |
| NFR-006 | ✅ | T018, T059 | |
| SEC-001 | ✅ | (via FR-013) | Duplicate of FR-013 (A-02) |
| SEC-002 | ⚠️ | T012, T053 | Validates PAT presence (masking + fail-fast on empty) only, not permission scoping (E-02) |
| SEC-003 | ✅ | T012, T019, T060 | |
| SEC-004 | ✅ | T012, T017 | T012 adds `::add-mask::` (SEC-004) |
| SEC-005 | ✅ | T016 | |
| SEC-006 | ✅ | (via FR-010) | Duplicate of FR-010 (A-01) |
| SEC-007 | ✅ | T015 | See B-02: grep pattern concerns |
| SEC-008 | ✅ | T007, T054 | |

---

## Metrics

| Metric | Value |
|--------|-------|
| Total Requirements | 29 (15 FR + 6 NFR + 8 SEC) |
| Total Tasks | 62 |
| Coverage % | 93% (27/29 fully covered; NFR-004 uncovered, SEC-002 partial) |
| Ambiguity Count | 3 |
| Requirement Duplication Count (Category A) | 3 |
| High Severity Finding Count | 1 (F-02) |
| Task Deduplication Finding Count | 2 (all recommendations for implementation phase) |
| Task Deduplication by Type | 1 no-action / 1 potential merge / 0 active overlap / 0 conflicting |
| Multi-Task Group Count | 0 |

---

### Category G Structured Findings

```json
[
  {
    "id": "G-01",
    "overlap_type": "none",
    "severity": "LOW",
    "task_ids": ["T034", "T061"],
    "dimensions": ["phase"],
    "rationale": "T034 (CI failure dispatch detection) and T061 (dedup guard happy-path verification) have distinct scopes — not duplicates. No action needed."
  },
  {
    "id": "G-02",
    "overlap_type": "overlapping",
    "severity": "MEDIUM",
    "task_ids": ["T031", "T046"],
    "dimensions": ["description"],
    "rationale": "RECOMMENDATION: T046 (manual timeout test) and T031 (CI log retrieval) share structured metadata concerns. Review overlap during implementation and consider consolidation."
  }
]
```

---
*Generated by Copilot SDK (claude-opus-4.6)*
