# Tasks: Dedicated PR Approver PAT (AGDT_PR_APPROVER_PAT)

## Phase Mapping: Plan → Tasks

| Plan Phase | Tasks Phase | Notes |
|------------|-------------|-------|
| Phase 1: Account & Secret Setup | Phase 1: Setup — Account & Secret Infrastructure | 1:1 mapping |
| Phase 2: Workflow Modification | Phase 2: Foundational + Phase 3: US1 + Phase 4: US2 | Plan phase split into prep, implementation, and degradation |
| Phase 3: Testing & Validation | Phase 5: US3 (Token Scope Isolation) | Isolation audit maps to plan's validation |
| Phase 4: Documentation | Phase 6: US4 (Documentation & Maintainer Guidance) | 1:1 mapping |
| (cross-cutting) | Final Phase: Polish & Cross-Cutting | Lint, perf verification, final FR check |

## Phase 1: Setup — Account & Secret Infrastructure

- [ ] T001 Create secondary GitHub account `ayaiayorg-pr-approver` for automated PR approvals
- [ ] T002 Add `ayaiayorg-pr-approver` to the `ayaiayorg` organization with Write role on `agentic-devtools` repository
- [ ] T003 Generate fine-grained PAT for `ayaiayorg-pr-approver` scoped to `ayaiayorg/agentic-devtools` with single permission `Pull requests: Write` (90-day expiry)
- [ ] T004 Configure repository secret `AGDT_PR_APPROVER_PAT` in Settings → Secrets → Actions

## Phase 2: Foundational — Workflow Preparation

- [ ] T005 Post-implementation verification: audit `.github/workflows/ai-pr-loop.yml` to confirm
  `AGDT_PR_APPROVER_PAT` is wired only via the `env` block of the "Run AI PR loop orchestrator"
  step and is not referenced by merge/comment paths (validates FR-002, FR-005 isolation)
  **Depends on**: T007
- [ ] T006 Identify the current approval implementation path ("Run AI PR loop orchestrator" step →
  `agdt-ai-pr-loop` → `orchestrator.py` → `provider.approve_pr()` → `gh api /pulls/{pr}/reviews` POST
  using `GH_TOKEN` env var) and confirm existing head-SHA safety behavior preserved per FR-004

## Phase 3: User Story 1 — Automated PR Approval with Approver PAT (P1)

- [x] T007 [US1] Add `AGDT_PR_APPROVER_PAT: ${{ secrets.AGDT_PR_APPROVER_PAT }}` to the "Run AI PR loop
  orchestrator" step `env` block in `.github/workflows/ai-pr-loop.yml` and update
  `agentic_devtools/cli/ci/github_provider.py` so `approve_pr()` uses `AGDT_PR_APPROVER_PAT`
  (when set) instead of the default `GH_TOKEN`, attributing the approval review to
  `ayaiayorg-pr-approver`
  (FR-001)
- [x] T008 [US1] Add inline workflow YAML comment above the `AGDT_PR_APPROVER_PAT` env entry explaining why a
  separate PAT is required (GitHub prevents approving your own PR) per FR-006
- [x] T009 [US1] Preserve head-SHA safety behavior in `agentic_devtools/cli/ci/github_provider.py` (FR-004) by
  ensuring `approve_pr()` continues to bind the approval to the expected `head_sha`/`commit_id` in the
  `POST /pulls/{pr}/reviews` call, avoiding logic regressions in approval targeting
- [ ] T011 [US1] [happy-path] End-to-end validation: trigger `ai-pr-loop` on a bot-authored PR and assert the approval review is created
  successfully and attributed to `ayaiayorg-pr-approver` (FR-001, FR-004)

## Phase 4: User Story 2 — Graceful Degradation for Missing PAT (P2)

- [x] T012 [US2] Add early-exit guard in `agentic_devtools/cli/ci/github_provider.py` `approve_pr()` that checks
  `AGDT_PR_APPROVER_PAT` is non-empty before the approval API call; when missing, log a warning and
  skip the approval (return without calling the API) (FR-003)
- [x] T013 [US2] Log a structured warning in `github_provider.py` naming `AGDT_PR_APPROVER_PAT` and corrective
  action when PAT is missing/empty, then skip approval (orchestrator continues without approving) (FR-003)
- [x] T014 [US2] Add explicit 401 (expired/invalid PAT) handling in `github_provider.py` `approve_pr()`
  try/except with clear authentication diagnostics logged, then skip approval gracefully (FR-003)
- [ ] T015 [US2] [negative-path] Validation: temporarily remove `AGDT_PR_APPROVER_PAT`, trigger workflow,
  and assert warning is logged and approval is skipped (orchestrator completes without approving) (FR-003)
- [ ] T028 [US2] [cross-cutting] Validate: use an invalid/expired `AGDT_PR_APPROVER_PAT`, trigger workflow,
  and assert 401 handling logs clear diagnostics and skips approval gracefully (FR-003)

## Phase 5: User Story 3 — Token Scope Isolation (P2)

- [ ] T010 [US3] Verify merge operations continue using their existing token path and do NOT consume `AGDT_PR_APPROVER_PAT` (FR-005)
- [ ] T016 [US3] [P] Verify via grep/audit that `AGDT_PR_APPROVER_PAT` appears ONLY in the orchestrator
  step `env` block and in `agentic_devtools/cli/ci/github_provider.py` (token selection for the approval
  API call), and is not referenced by merge/comment code paths across the workflow or Python source
  (FR-002)
- [ ] T017 [US3] [P] Verify the merge step and all comment-posting steps continue using `GITHUB_TOKEN` or `COPILOT_GITHUB_TOKEN` unchanged (FR-002, FR-005)
- [ ] T018 [US3] [P] Confirm the token is never echoed, interpolated into shell commands, or logged in the script body (NFR-003 compliance)

## Phase 6: User Story 4 — Documentation & Maintainer Guidance (P3)

- [x] T019 [US4] [P] Add documentation section describing `AGDT_PR_APPROVER_PAT`: purpose, required permissions (fine-grained, `Pull requests: Write`, single-repo scope), and rotation procedure
  (FR-007) in `docs/` or `CONTRIBUTING.md`
- [x] T020 [US4] [P] Document troubleshooting guidance for common errors: 401 (expired PAT), 403 (insufficient access), self-approval misconfiguration (FR-007)
- [x] T022 [US4] [P] Document the 90-day PAT rotation schedule and steps to rotate the secret
- [ ] T023 [US4] Validate that the inline workflow comment added by T008 explaining the separate-identity rationale is present and accurate (FR-006)
- [ ] T024 [US4] Verify documentation completeness: confirm docs section covers PAT purpose, permissions, rotation procedure, and troubleshooting (FR-007)

## Final Phase: Polish & Cross-Cutting

- [ ] T025 Run full workflow YAML lint/validation to ensure no syntax errors in `.github/workflows/ai-pr-loop.yml`
- [ ] T026 [cross-cutting] Verify no unintended changes to workflow execution time (NFR-001) — the guard is a string-empty check with no API calls
- [ ] T027 Final review: confirm all FRs are satisfied (FR-001 through FR-007) and all acceptance scenarios pass

## Dependency Graph

```text
T001 → T002 → T003 → T004 (sequential account setup)
T004 → T007 (secret must exist before workflow references it)
T006 → T007 (understand baseline before modifying)
T007 → T005 (post-change isolation verification requires implementation)
T007 → T008, T009, T010 (approval-step modification enables verification)
T007 → T012 (guard added to approval path)
T012 → T013, T014 (guard logic before error handling)
T007 + T012 → T011, T015, T028 (validation requires both changes)
T007 → T016, T017, T018 (isolation audit after change)
T007 → T019, T020, T022 (documentation after implementation)
T008 → T023 (inline comment must exist before validation)
T019, T020, T022 → T024 (documentation must exist before verification)
T011 + T015 + T028 + T016–T018 + T023 + T024 → T025–T027 (polish after validation)
```

## FR Traceability Matrix

| FR | Tasks |
|-----|-------|
| FR-001 | T007, T011 |
| FR-002 | T005, T016, T017 |
| FR-003 | T012, T013, T014, T015, T028 |
| FR-004 | T006, T009, T011 |
| FR-005 | T005, T010, T017 |
| FR-006 | T008, T023 |
| FR-007 | T019, T020, T022, T024 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
