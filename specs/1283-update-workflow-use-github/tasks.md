# Tasks: GitHub App Token for Copilot Review Requests

**Issue**: [#1283](https://github.com/ayaiayorg/agentic-devtools/issues/1283)

---

## Phase 1: Setup

- [ ] T001 Audit all references to `secrets.COPILOT_GITHUB_TOKEN` across `.github/workflows/`, `.github/scripts/`, docs, and tests to establish baseline (FR-005 inventory)
- [ ] T002 Verify `actions/create-github-app-token@v1` action availability and confirm pinning strategy aligns with existing `actions/checkout@v4`, `actions/github-script@v7` pattern

---

## Phase 2: Foundational

- [ ] T003 Define the reusable App token generation + validation step pattern (YAML snippet) to be inserted consistently across all three workflows (FR-001, FR-009): step id `app_token`, inputs
  `secrets.COPILOT_APP_ID` / `secrets.COPILOT_APP_PRIVATE_KEY`, followed by a validation step that checks `steps.app_token.outputs.token` is non-empty with actionable error referencing App credentials
  and installation URL (NFR-003)

---

## Phase 3: User Story 1 — Phase Progression Workflow (P1)

- [ ] T004 [US1] Replace `"Validate Copilot Token"` bash step in `.github/workflows/speckit-phase-progression.yml` with `actions/create-github-app-token@v1` step (id: `app_token`) and validation step,
  preserving existing `if:` conditional gate (FR-001, FR-004)
- [ ] T005 [US1] Update `"Generate Phase Artifacts"` step env block in `.github/workflows/speckit-phase-progression.yml`: change `COPILOT_GITHUB_TOKEN` value from `${{ secrets.COPILOT_GITHUB_TOKEN }}`
  to `${{ steps.app_token.outputs.token }}` — env-var name preserved for SDK compatibility (FR-002, FR-003)
- [ ] T006 [US1] Update `"Request Copilot Review"` step `github-token` input in `.github/workflows/speckit-phase-progression.yml` from `secrets.COPILOT_GITHUB_TOKEN` to `steps.app_token.outputs.token`
  (FR-002)
- [ ] T007 [US1] Update `"Handle Failure (Comment + Label)"` step troubleshooting body text in `.github/workflows/speckit-phase-progression.yml` to reference `COPILOT_APP_ID` /
  `COPILOT_APP_PRIVATE_KEY` instead of `COPILOT_GITHUB_TOKEN` (FR-006)
- [ ] T008 [US1] Remove all remaining `secrets.COPILOT_GITHUB_TOKEN` references in `.github/workflows/speckit-phase-progression.yml` and verify zero occurrences (FR-005)
- [ ] T009 [US1] Verify idempotency guard logic (skip review if Copilot already requested) still functions with App token in `.github/workflows/speckit-phase-progression.yml` — no behavioral change
  expected since App token can read reviewer lists identically (FR-010)

---

## Phase 4: User Story 2 — Issue Trigger Workflow (P1)

- [ ] T010 [US2] Replace `"Validate Copilot Token"` bash step in `.github/workflows/speckit-issue-trigger.yml` with `actions/create-github-app-token@v1` step (id: `app_token`) and validation step,
  preserving existing `if:` conditional gate (FR-001, FR-004)
- [ ] T011 [US2] Update `"Generate Specification"` step env block in `.github/workflows/speckit-issue-trigger.yml`: change `COPILOT_GITHUB_TOKEN` value from `${{ secrets.COPILOT_GITHUB_TOKEN }}` to
  `${{ steps.app_token.outputs.token }}` — env-var name preserved for SDK compatibility (FR-002, FR-003)
- [ ] T012 [US2] Update `"Request Copilot Review"` step `github-token` input in `.github/workflows/speckit-issue-trigger.yml` from `secrets.COPILOT_GITHUB_TOKEN` to `steps.app_token.outputs.token`
  (FR-002)
- [ ] T013 [US2] Update `"Post Failed Comment"` step troubleshooting body text in `.github/workflows/speckit-issue-trigger.yml` to reference `COPILOT_APP_ID` / `COPILOT_APP_PRIVATE_KEY` instead of
  `COPILOT_GITHUB_TOKEN` (FR-006)
- [ ] T014 [US2] Remove all remaining `secrets.COPILOT_GITHUB_TOKEN` references in `.github/workflows/speckit-issue-trigger.yml` and verify zero occurrences (FR-005)
- [ ] T015 [US2] Verify idempotency guard logic still functions with App token in `.github/workflows/speckit-issue-trigger.yml` (FR-010)

---

## Phase 5: User Story 3 — Copilot Review Request Workflow (P1)

- [ ] T016 [US3] Replace `"Validate Copilot Token"` bash step in `.github/workflows/speckit-copilot-review-request.yml` with `actions/create-github-app-token@v1` step (id: `app_token`) and validation
  step (FR-001, FR-004)
- [ ] T017 [US3] Update `idempotency` step `github-token` input in `.github/workflows/speckit-copilot-review-request.yml` from `secrets.COPILOT_GITHUB_TOKEN` to `steps.app_token.outputs.token`
  (FR-002)
- [ ] T018 [US3] Update `request-copilot-review` step `github-token` input in `.github/workflows/speckit-copilot-review-request.yml` from `secrets.COPILOT_GITHUB_TOKEN` to
  `steps.app_token.outputs.token` (FR-002)
- [ ] T019 [US3] Remove all remaining `secrets.COPILOT_GITHUB_TOKEN` references in `.github/workflows/speckit-copilot-review-request.yml` and verify zero occurrences (FR-005)
- [ ] T020 [US3] Verify idempotency guard logic still functions with App token in `.github/workflows/speckit-copilot-review-request.yml` (FR-010)

---

## Phase 6: User Story 4 — Documentation Updates (P2)

- [ ] T021 [P] [US4] Update `README.md` "Required Secrets" table: replace `COPILOT_GITHUB_TOKEN` row with `COPILOT_APP_ID` and `COPILOT_APP_PRIVATE_KEY` rows including App permissions note
  (`Pull requests: Read & Write`, `Contents: Read`) (FR-007)
- [ ] T022 [P] [US4] Update `CONTRIBUTING.md` "Required Secrets" table: replace `COPILOT_GITHUB_TOKEN` row with `COPILOT_APP_ID` and `COPILOT_APP_PRIVATE_KEY` rows identical to README (FR-008)
- [ ] T023 [P] [US4] Update docstring and error message in `.github/scripts/speckit-trigger/copilot_generate.py` to describe `COPILOT_GITHUB_TOKEN` env-var as "provided by workflow via GitHub App
  token" instead of "Fine-grained PAT" (FR-006)
- [ ] T024 [P] [US4] Update env header comment and `:?` error text in `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` to describe token source as GitHub App (FR-006)
- [ ] T025 [P] [US4] Update troubleshooting list item in `.github/scripts/speckit-trigger/templates/failed.md` from "Verify COPILOT_GITHUB_TOKEN" to "Verify COPILOT_APP_ID and COPILOT_APP_PRIVATE_KEY
  secrets are configured" (FR-006)

---

## Phase 7: User Story 5 — Stale PAT Removal Verification (P3)

- [ ] T026 [US5] Run `grep -r 'secrets\.COPILOT_GITHUB_TOKEN' .github/` and verify zero results across all workflow files (SC-001, FR-005)
- [ ] T027 [US5] Run `grep -r 'COPILOT_GITHUB_TOKEN' README.md CONTRIBUTING.md` and verify zero results (SC-002)
- [ ] T028 [US5] Verify no other files in the repository reference `secrets.COPILOT_GITHUB_TOKEN` (full repo grep)

---

## Phase 8: Polish & Cross-Cutting

- [ ] T029 Update test assertions/mocks in `tests/workflows/test_copilot_generate.py` that reference `COPILOT_GITHUB_TOKEN` secret description to reflect App-based authentication
- [ ] T030 Check `.github/ISSUE_TEMPLATE/speckit-test.md` for any `COPILOT_GITHUB_TOKEN` references and update to App credentials if found
- [ ] T031 Verify all three workflows use identical step id `app_token` and consistent output reference `steps.app_token.outputs.token` (FR-009)
- [ ] T032 Verify validation step error messages across all three workflows include actionable guidance: exact secret names (`COPILOT_APP_ID`, `COPILOT_APP_PRIVATE_KEY`) and installation URL (NFR-003,
  FR-006)
- [ ] T033 Final end-to-end verification: confirm `actions/create-github-app-token@v1` step placement is before all token-consuming steps in each workflow (FR-009)

---

## Dependencies

| Task | Depends On |
|------|-----------|
| T004–T009 | T003 |
| T010–T015 | T003 |
| T016–T020 | T003 |
| T021–T025 | None (parallelizable with Phase 3–5) |
| T026–T028 | T008, T014, T019, T021, T022 |
| T029–T030 | T003 |
| T031–T033 | T008, T014, T019 |

## FR Traceability Matrix

| FR | Tasks |
|----|-------|
| FR-001 | T003, T004, T010, T016 |
| FR-002 | T005, T006, T011, T012, T017, T018 |
| FR-003 | T005, T011 |
| FR-004 | T004, T010, T016 |
| FR-005 | T001, T008, T014, T019, T026, T028 |
| FR-006 | T007, T013, T023, T024, T025, T032 |
| FR-007 | T021 |
| FR-008 | T022 |
| FR-009 | T003, T031, T033 |
| FR-010 | T009, T015, T020 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
