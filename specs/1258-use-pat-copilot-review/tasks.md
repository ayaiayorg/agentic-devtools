# Tasks: Use PAT for Copilot Review Request in SpecKit Workflows

**Issue**: [#1258](https://github.com/ayaiayorg/agentic-devtools/issues/1258)

## Phase 1: Setup

- [ ] T001 Audit current "Request Copilot Review" step in `.github/workflows/speckit-phase-progression.yml` — confirm line range, existing `actions/github-script@v7` usage, absence of `github-token`
  input, and `continue-on-error: true` setting
- [ ] T002 [P] Audit current "Request Copilot Review" step in `.github/workflows/speckit-issue-trigger.yml` — confirm line range, existing `actions/github-script@v7` usage, absence of `github-token`
  input, and `continue-on-error: true` setting
- [ ] T003 [P] Audit current "Request Copilot Review" and "Check existing reviewers" steps in `.github/workflows/speckit-copilot-review-request.yml` — confirm line range, absence of `github-token`
  input, and note that no "Validate Copilot Token" step exists
- [ ] T004 [P] Audit existing "Validate Copilot Token" steps in `speckit-phase-progression.yml` and `speckit-issue-trigger.yml` — document current error message text and permission guidance for
  comparison with updated messages

## Phase 2: Foundational

- [ ] T005 Verify that no other `actions/github-script@v7` steps in any of the three workflow files reference `github-token` in a way that would conflict with the planned changes (depends on: T001,
  T002, T003)
- [ ] T006 Verify that "Post Completed Comment", "Post Review Request Status", and other non-reviewer steps in all three workflows use default `GITHUB_TOKEN` and do not need the PAT override (depends
  on: T005)

## Phase 3: User Story 1 — Copilot Review on Phase-Progression PRs (P1)

- [ ] T007 [US1] Add `github-token: ${{ secrets.COPILOT_GITHUB_TOKEN }}` to the "Request Copilot Review" `actions/github-script@v7` step in `.github/workflows/speckit-phase-progression.yml` (depends
  on: T005)
- [ ] T008 [US1] Update the "Validate Copilot Token" step error message in `.github/workflows/speckit-phase-progression.yml` to include accurate minimum permissions: "Add a fine-grained PAT with 'Pull
  requests: Write' and 'Copilot Requests: Read' permissions, or a classic PAT with 'repo' scope. The token owner must be a repository collaborator with Copilot access." (depends on: T004)
- [ ] T009 [US1] Validate YAML syntax of `.github/workflows/speckit-phase-progression.yml` after edits — confirm no indentation errors (depends on: T007, T008)

## Phase 4: User Story 2 — Copilot Review on Issue-Trigger PRs (P1)

- [ ] T010 [US2] Add `github-token: ${{ secrets.COPILOT_GITHUB_TOKEN }}` to the "Request Copilot Review" `actions/github-script@v7` step in `.github/workflows/speckit-issue-trigger.yml` (depends on:
  T005)
- [ ] T011 [US2] Update the "Validate Copilot Token" step error message in `.github/workflows/speckit-issue-trigger.yml` to include accurate minimum permissions: "Add a fine-grained PAT with 'Pull
  requests: Write' and 'Copilot Requests: Read' permissions, or a classic PAT with 'repo' scope. The token owner must be a repository collaborator with Copilot access." (depends on: T004)
- [ ] T012 [US2] Validate YAML syntax of `.github/workflows/speckit-issue-trigger.yml` after edits — confirm no indentation errors (depends on: T010, T011)

## Phase 5: User Story 3 — Copilot Review on Implementation PRs (P1)

- [ ] T013 [US3] Add `github-token: ${{ secrets.COPILOT_GITHUB_TOKEN }}` to the "Request Copilot Review" `actions/github-script@v7` step in `.github/workflows/speckit-copilot-review-request.yml`
  (depends on: T005)
- [ ] T014 [US3] Add `github-token: ${{ secrets.COPILOT_GITHUB_TOKEN }}` to the "Check existing reviewers" (`id: idempotency`) `actions/github-script@v7` step in
  `.github/workflows/speckit-copilot-review-request.yml` for consistency — ensures same authenticated identity for read and write operations (depends on: T005)
- [ ] T015 [US3] Add a new "Validate Copilot Token" step in `.github/workflows/speckit-copilot-review-request.yml` **before** the "Check existing reviewers" step, using the shell pattern from the
  other two workflows, with error message: "Add a fine-grained PAT with 'Pull requests: Write' permission, or a classic PAT with 'repo' scope. The token owner must be a repository collaborator with
  Copilot access." (depends on: T005)
- [ ] T016 [US3] Validate YAML syntax of `.github/workflows/speckit-copilot-review-request.yml` after edits — confirm no indentation errors (depends on: T013, T014, T015)

## Phase 6: User Story 4 — Consistent Token Usage Across All Workflows (P2)

- [ ] T017 [US4] Cross-file audit: confirm all three "Request Copilot Review" steps reference the identical secret `${{ secrets.COPILOT_GITHUB_TOKEN }}` via the `github-token` input (depends on: T009,
  T012, T016)
- [ ] T018 [US4] Cross-file audit: confirm the `id: idempotency` step in `speckit-copilot-review-request.yml` also uses `${{ secrets.COPILOT_GITHUB_TOKEN }}` (depends on: T014)
- [ ] T019 [US4] Cross-file audit: confirm all three "Validate Copilot Token" steps reference the same secret name `COPILOT_GITHUB_TOKEN` in their `env` block (depends on: T008, T011, T015)

## Phase 7: User Story 5 — Graceful Degradation (P3)

- [ ] T020 [US5] Verify that `continue-on-error: true` is preserved on the "Request Copilot Review" step in `.github/workflows/speckit-phase-progression.yml` after changes (depends on: T007)
- [ ] T021 [US5] [P] Verify that `continue-on-error: true` is preserved on the "Request Copilot Review" step in `.github/workflows/speckit-issue-trigger.yml` after changes (depends on: T010)
- [ ] T022 [US5] [P] Verify that `continue-on-error: true` is preserved on the "Request Copilot Review" step in `.github/workflows/speckit-copilot-review-request.yml` after changes (depends on: T013)
- [ ] T023 [US5] Verify that existing idempotency logic (422 "already requested" detection, reviewer/review existence checks) is unchanged in all three workflow files (depends on: T007, T010, T013,
  T014)

## Phase 8: Polish & Cross-Cutting

- [ ] T024 Run full YAML lint validation across all three modified workflow files (depends on: T009, T012, T016)
- [ ] T025 Verify that no step other than "Request Copilot Review" and "Check existing reviewers" had its behavior altered — diff review of all three files against `main` (depends on: T024)
- [ ] T026 Verify `copilot_review_requested` output variable is still set correctly in all three workflows' "Request Copilot Review" steps (depends on: T007, T010, T013)
- [ ] T027 Commit changes with a conventional commit message that follows `COMMIT_CONVENTION.md`, using
  [#1258](https://github.com/ayaiayorg/agentic-devtools/issues/1258) as the markdown issue link in both the scope and footer (depends on: T017, T018, T019, T023, T024, T025, T026)

---
*Generated by Copilot SDK (claude-opus-4.6)*
