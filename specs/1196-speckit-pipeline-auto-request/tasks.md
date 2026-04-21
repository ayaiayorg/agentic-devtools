# Tasks: SpecKit Pipeline — Auto-Request Copilot Review After PR Creation

**Feature Branch**: `1196-speckit-pipeline-auto-request`
**Source Issue**: [#1196](https://github.com/ayaiayorg/agentic-devtools/issues/1196)

---

## Phase 1: Setup

- [ ] T001 [P] Research `.github/workflows/speckit-issue-trigger.yml` — identify PR creation step ID, step outputs, and comment step structure
- [ ] T002 [P] Research `.github/workflows/speckit-phase-progression.yml` — identify PR creation step ID, step outputs, and comment step structure
- [ ] T003 [P] Research `.github/workflows/copilot-review-gate.yml` — extract bot reviewer login, `continue-on-error` pattern, and permission declarations
- [ ] T004 [P] Research `.github/workflows/speckit-implement-trigger.yml` — understand implementation PR lifecycle, agent bot login, and label conventions

---

## Phase 2: Foundational

- [ ] T005 Verify `.github/scripts/speckit-trigger/create-spec-pr.sh` exposes `pr_number` as a step output consumable by downstream workflow steps
  - Depends on: T001, T002
- [ ] T006 Confirm `copilot-pull-request-reviewer[bot]` is the correct reviewer login used across existing gate workflows
  - Depends on: T003

---

## Phase 3: US-002 — Auto-Request Copilot Review for Implementation PRs

- [ ] T007 [US2] Create `.github/workflows/speckit-copilot-review-request.yml` with `pull_request` trigger for types `opened` and `labeled` on branch `main`
  - Depends on: T004, T006
- [ ] T008 [US2] Declare minimal job-level permissions in `.github/workflows/speckit-copilot-review-request.yml`: `pull-requests: write`, `issues: write`, `contents: read`
  - Depends on: T007
- [ ] T009 [US2] Add job-level `if` condition in `.github/workflows/speckit-copilot-review-request.yml` gating on author `copilot-swe-agent[bot]`
  for `opened` events and label `speckit:implementation` for `labeled` events
  - Depends on: T008
- [ ] T010 [US2] Add `github-script` idempotency guard step (`id: idempotency`) in `.github/workflows/speckit-copilot-review-request.yml` — check whether
  Copilot is already a requested reviewer or active reviewer before requesting, and set output `already_requested`
  - Depends on: T009
- [ ] T011 [US2] Add `github-script` step in `.github/workflows/speckit-copilot-review-request.yml` to request Copilot reviewer via
  `github.rest.pulls.requestReviewers()` with `continue-on-error: true` and `core.warning()` on failure,
  gated on `steps.idempotency.outputs.already_requested != 'true'`
  - Depends on: T010
- [ ] T012 [US2] Add `github-script` step in `.github/workflows/speckit-copilot-review-request.yml` to extract linked issue number from PR title or body using regex `#(\d+)` and set output
  `issue_number`
  - Depends on: T011

---

## Phase 4: US-001 — Auto-Request Copilot Review for Spec PRs

- [ ] T013 [P] [US1] Add "Request Copilot Review" `github-script` step with `id: request-copilot-review`
  in `.github/workflows/speckit-issue-trigger.yml` after the `create-pr` step
  gated on `steps.create-pr.outputs.pr_number != ''`, calling
  `github.rest.pulls.requestReviewers()` with `continue-on-error: true` and
  `core.warning()` on failure, setting output `copilot_review_requested` to `'true'` or `'false'`
  - Depends on: T005, T006
- [ ] T014 [P] [US1] Add "Request Copilot Review" `github-script` step with `id: request-copilot-review`
  in `.github/workflows/speckit-phase-progression.yml` after the `create-pr` step
  gated on `steps.create-pr.outputs.pr_number != ''`, calling
  `github.rest.pulls.requestReviewers()` with `continue-on-error: true` and
  `core.warning()` on failure, setting output `copilot_review_requested` to `'true'` or `'false'`
  - Depends on: T005, T006

---

## Phase 5: US-003 — Visible Status in Issue Comments

- [ ] T015 [P] [US3] Update the "Post Completed Comment" `github-script` step in `.github/workflows/speckit-issue-trigger.yml` to read `steps.request-copilot-review.outputs.copilot_review_requested`
  and append `🤖 Copilot review requested` on success or `⚠️ Copilot review request failed` on failure
  - Depends on: T013
- [ ] T016 [P] [US3] Update the "Post Phase Progress Comment" `github-script` step in `.github/workflows/speckit-phase-progression.yml` to read
  `steps.request-copilot-review.outputs.copilot_review_requested` and append the corresponding status line
  - Depends on: T014
- [ ] T017 [US3] Add `github-script` step in `.github/workflows/speckit-copilot-review-request.yml` to post a status comment on the linked issue (from T012 output) with `🤖 Copilot review requested` or
  `⚠️ Copilot review request failed` based on the review request step outcome
  - Depends on: T012
- [ ] T018 [US3] Add duplicate comment detection in the issue-comment step of `.github/workflows/speckit-copilot-review-request.yml` — before posting, check for an existing status comment for the same
  PR number and update or skip to prevent misleading duplicates on re-triggered `labeled` events
  - Depends on: T017

---

## Final Phase: Polish & Cross-Cutting

- [ ] T019 Validate YAML syntax for all new and modified workflow files (`.github/workflows/speckit-copilot-review-request.yml`, `.github/workflows/speckit-issue-trigger.yml`,
  `.github/workflows/speckit-phase-progression.yml`)
  - Depends on: T015, T016, T018
- [ ] T020 Verify `.github/scripts/speckit-trigger/create-spec-pr.sh` has zero modifications — confirm no reviewer-request logic was added to the shell script (AC-007)
  - Depends on: T019
- [ ] T021 Verify permissions in `.github/workflows/speckit-copilot-review-request.yml` are self-contained and no permission changes were made to `.github/workflows/speckit-implement-trigger.yml`
  (AC-008)
  - Depends on: T019
- [ ] T022 Verify idempotency — confirm that a `labeled` event firing after a successful `opened` event produces no duplicate comments, no API errors, and no misleading status output
  - Depends on: T019
- [ ] T023 Verify `continue-on-error: true` plus `core.warning()` failure-handling pattern in all new steps matches the existing convention in `.github/workflows/copilot-review-gate.yml` (FR-009)
  - Depends on: T019
- [ ] T024 Review all `if` conditions across new and modified steps for correctness, edge-case safety, and alignment with the specification's edge cases section
  - Depends on: T019

---
*Generated by Copilot SDK (claude-opus-4.6)*
