# Tasks: AI PR Loop Automated Agentic Repair

**Issue**: [#1359](https://github.com/ayaiayorg/agentic-devtools/issues/1359)

---

## Phase 1: Setup — Project Scaffolding & Configuration

- [ ] T001 Add `AGDT_VERSION` env variable to the top-level `env:` block in `.github/workflows/ai-pr-loop.yml` (e.g., `AGDT_VERSION: '0.42.0'`) as the single source of truth for the pinned
  `agentic-devtools` version used by the repair job

---

## Phase 2: Foundational — Dispatch Decision & Deduplication Guard

- [ ] T002 Add dispatch-decision step to the `ai-pr-loop` job in `.github/workflows/ai-pr-loop.yml` after the `check-review` step and before the `merge-check` step. This step evaluates whether a
  repair is needed when the PR is blocked by actionable Copilot review comments (CHANGES_REQUESTED with inline comments per **FR-001**) OR failing required CI checks, AND merge is not possible, AND
  the lint patch step did NOT push. It reuses existing `PRIVILEGED_PATH_PREFIXES` (FR-010), fork guard (FR-013), and `ai-pr-loop-ignore` label check (FR-014)
- [ ] T003 Implement deduplication guard logic within the dispatch-decision step (`.github/workflows/ai-pr-loop.yml`). Search PR comments for `<!-- repair-dispatch:FULL_SHA:` prefix matching current
  `head_sha` (FR-007). If found with count ≥ 3: skip dispatch and PATCH the comment to "human intervention required". If found with count < 3: increment count via `github.rest.issues.updateComment`.
  If not found: create new marker comment with COUNT=1 and status "pending"
  - Depends on: T002
- [ ] T004 Implement Docker/privileged-file detection within the dispatch-decision step (`.github/workflows/ai-pr-loop.yml`). Check if PR modifies `Dockerfile`, `docker-compose.yml`, or
  `docker-compose.yaml` (SEC-008). If so, skip repair dispatch and post comment flagging for human review
  - Depends on: T002
- [ ] T005 Determine repair type and set job outputs from the dispatch-decision step (`.github/workflows/ai-pr-loop.yml`): `repair_needed` (`true`/`false`), `repair_type` (`review`/`ci`/`both`),
  `review_url` (GitHub review URL), `pr_number`, `head_sha`, `head_branch`. Add these as `outputs:` on the `ai-pr-loop` job definition
  - Depends on: T002, T003, T004
- [ ] T006 Ensure the dispatch-decision step respects the existing 50-cycle outer loop limit (**FR-011**) by confirming the step only runs when `steps.guards.outputs.should_proceed == 'true'` (the
  guards step already enforces the 50-cycle limit in `.github/workflows/ai-pr-loop.yml`)
  - Depends on: T002

---

## Phase 3: User Story 1 — Automated Copilot Review Comment Resolution (P1)

### Tests

- [ ] T007 [P] [US1] Create a manual test plan document (in-memory, not committed) for review comment repair: create a test PR with intentional issues, trigger Copilot review, observe dispatch →
  repair → push → re-review cycle, verify repair comment posted, threads resolved, Copilot re-requested (FR-001, FR-009)
- [ ] T051 [US1] Verify the dispatch-decision step correctly identifies actionable Copilot review comments (CHANGES_REQUESTED with inline comments) and sets `repair_needed=true`,
  `repair_type='review'` (FR-001, happy-path)
  - Depends on: T002, T005
- [ ] T052 [US1] Verify the `agentic-repair` job specifies `runs-on: ubuntu-latest` in `.github/workflows/ai-pr-loop.yml` (FR-003, happy-path)
  - Depends on: T011
- [ ] T053 [US1] Verify PAT masking (`::add-mask::`) is applied to `COPILOT_GITHUB_TOKEN` and the validation step exits with a clear error when the secret is empty (FR-004, happy-path, negative)
  - Depends on: T012
- [ ] T054 [US1] Verify the repair job posts a "started" comment with workflow run link at dispatch and updates it to "completed"/"failed" on job finish (FR-008, happy-path)
  - Depends on: T023, T025
- [ ] T055 [US1] Verify Copilot review is re-requested after the repair agent pushes fixes, confirming the reviewer appears in the requested reviewers list (FR-009, happy-path)
  - Depends on: T026
- [ ] T059 [US1] Verify the `agentic-repair` job installs `agentic-devtools` from PyPI at the pinned version (not from the PR branch) and that agent prompts are sourced from the
  `__trusted_main` checkout (FR-005, happy-path)
  - Depends on: T013, T017

### CI-Safe Prompt

- [ ] T008 [US1] Create CI-safe prompt file at `.github/prompts/agdt.address-copilot-review.ci-repair.prompt.md` by copying from `.github/prompts/agdt.address-copilot-review.prompt.md`. Remove Phase 4
  test execution (`agdt-test`, `agdt-task-wait` blocks). Add explicit constraints: "Do NOT run `pytest`, `agdt-test`, `bash scripts/*.sh`, or any PR-sourced executable" and "Do NOT install packages
  from the PR branch (`pip install .`)". Add note: "Verification is delegated to the subsequent CI run". Retain: triage, code edits (using `ruff check --fix`, `ruff format`), commit, push, reply,
  resolve threads, re-request review
- [ ] T009 [P] [US1] Create CI-safe agent definition at `.github/agents/agdt.address-copilot-review.ci-repair.agent.md` pointing to the CI-safe prompt with CI-repair scope documented
  - Depends on: T008
- [ ] T010 [P] [US1] Add `AGDT_CI_REPAIR_MODE` environment variable defense-in-depth note at the top of `.github/prompts/agdt.address-copilot-review.prompt.md`: "If `AGDT_CI_REPAIR_MODE=1` is set,
  skip all test execution steps" (SEC-003)

### Repair Job — Core Definition

- [ ] T011 [US1] Define the `agentic-repair` job skeleton in `.github/workflows/ai-pr-loop.yml` with: `needs: ai-pr-loop`, `if: needs.ai-pr-loop.outputs.repair_needed == 'true'`, `runs-on:
  ubuntu-latest` (FR-003), `timeout-minutes: 15` (FR-012), inherits workflow-level concurrency group (NFR-005) and permissions
  - Depends on: T005
- [ ] T012 [US1] Add PAT masking and validation step in the `agentic-repair` job (`.github/workflows/ai-pr-loop.yml`): `echo "::add-mask::${COPILOT_GITHUB_TOKEN}"` (SEC-004, NFR-003). Fail fast if
  `COPILOT_GITHUB_TOKEN` is empty with clear error message (NFR-006). The PAT authenticates using `secrets.COPILOT_GITHUB_TOKEN` (**FR-004**) scoped to Contents R/W, Pull requests R/W,
  Issues R/W (repair marker comments), Checks Read (check-runs/check-suites), Actions Read (SEC-002)
  - Depends on: T011
- [ ] T013 [US1] Add trusted `main` branch checkout step in the `agentic-repair` job (`.github/workflows/ai-pr-loop.yml`): `actions/checkout@v4` with `ref: main`, `path: __trusted_main`. Agent prompts
  and instructions are sourced from this trusted checkout, not the PR branch (FR-005, SEC-003)
  - Depends on: T011
- [ ] T014 [US1] Add PR branch checkout step in the `agentic-repair` job (`.github/workflows/ai-pr-loop.yml`): `actions/checkout@v4` with `ref: ${{ needs.ai-pr-loop.outputs.head_sha }}`, `path:
  pr-worktree`, `persist-credentials: false` (SEC-003)
  - Depends on: T011
- [ ] T015 [US1] Add git credential configuration and branch restoration step in the `agentic-repair` job (`.github/workflows/ai-pr-loop.yml`): `git remote set-url origin` with COPILOT_GITHUB_TOKEN,
  `git checkout -B` to switch from detached HEAD to the actual PR branch
  - Depends on: T014
- [ ] T016 [US1] Add Python 3.12 setup step using `actions/setup-python@v5` in the `agentic-repair` job (`.github/workflows/ai-pr-loop.yml`)
  - Depends on: T011
- [ ] T017 [US1] Add `agentic-devtools` installation step from PyPI at pinned version (`pip install agentic-devtools==${{ env.AGDT_VERSION }}`) in the `agentic-repair` job
  (`.github/workflows/ai-pr-loop.yml`) — FR-005: install from trusted source, never from PR branch
  - Depends on: T001, T016
- [ ] T018 [US1] Add `ruff` and `markdownlint-cli2` installation step at pinned versions in the `agentic-repair` job (`.github/workflows/ai-pr-loop.yml`) — SEC-003: only pinned trusted tooling
  - Depends on: T016
- [ ] T019 [US1] Add Copilot CLI installation step in the `agentic-repair` job (`.github/workflows/ai-pr-loop.yml`): `agdt-setup-copilot-cli` for standalone binary, plus `gh extension install
  github/gh-copilot` as fallback (FR-005). Validate binary availability before proceeding
  - Depends on: T017

### Repair Job — PR State Validation

- [ ] T020 [US1] Add PR state validation step in the `agentic-repair` job (`.github/workflows/ai-pr-loop.yml`): check if PR is still open (not merged/closed — exit cleanly if terminal), check if head
  SHA still matches (another push may have occurred), check for merge conflicts (report and exit if present)
  - Depends on: T015

### Repair Job — Prompt Rendering & Session

- [ ] T021 [US1] Add prompt rendering step in the `agentic-repair` job (`.github/workflows/ai-pr-loop.yml`): read CI-safe prompt from
  `__trusted_main/.github/prompts/agdt.address-copilot-review.ci-repair.prompt.md`. For review-triggered repairs: inject the review URL. Write rendered prompt to `/tmp/repair-prompt.md`
  - Depends on: T008, T013, T020
- [ ] T022 [US1] Add secret-scanning guard instruction to the CI-safe prompt
  (`.github/prompts/agdt.address-copilot-review.ci-repair.prompt.md`) — SEC-007: instruct the agent to run
  `git diff HEAD --staged | grep -iqE '(token|password|secret|api_key|private_key)'` before pushing and abort if matches found
  - Depends on: T008
- [ ] T023 [US1] Add repair comment status update step ("started") in the `agentic-repair` job (`.github/workflows/ai-pr-loop.yml`): PATCH the marker comment created by dispatch-decision to update
  status to "started" and add workflow run link (FR-008)
  - Depends on: T011, T003
- [ ] T024 [US1] Add Copilot session execution step in the `agentic-repair` job (`.github/workflows/ai-pr-loop.yml`): set `GH_TOKEN` from `secrets.COPILOT_GITHUB_TOKEN`, set `AGDT_CI_REPAIR_MODE=1`.
  Use Python wrapper that calls `start_copilot_session()` from `agentic_devtools.cli.copilot.session`, checks `.process` attribute, waits for completion, and propagates non-zero exit code. Include
  fallback to standalone `copilot --allow-all -p` with file-reference instruction
  - Depends on: T019, T021
- [ ] T025 [US1] Add completion/failure handling step in the `agentic-repair` job (`.github/workflows/ai-pr-loop.yml`): on success PATCH repair comment to "completed" with outcome summary; on
  failure/timeout PATCH to "failed" with details and "human intervention required" (FR-008)
  - Depends on: T024
- [ ] T026 [US1] Add Copilot review re-request step after the agent session completes successfully in the `agentic-repair` job (`.github/workflows/ai-pr-loop.yml`) — **FR-009**: re-request Copilot
  review after pushing fixes so the loop can naturally re-trigger. Use `github.rest.pulls.requestReviewers` with `reviewers: ['Copilot']`
  - Depends on: T025

---

## Phase 4: User Story 4 — Separation of Responsibilities (P1)

- [ ] T027 [US4] Verify the `agentic-repair` job in `.github/workflows/ai-pr-loop.yml` does NOT contain any approve or merge API calls (`pulls.createReview` with `APPROVE`, `pulls.merge`) — FR-006:
  these remain exclusively in the `ai-pr-loop` job. Add a code comment documenting this security invariant
  - Depends on: T025
- [ ] T060 [US4] Verify the `agentic-repair` job's scope is limited to code changes, comment replies, thread resolution, and re-requesting review — no approve or merge capabilities present (FR-006, happy-path)
  - Depends on: T027
- [ ] T028 [US4] Add explicit constraint in the CI-safe prompt (`.github/prompts/agdt.address-copilot-review.ci-repair.prompt.md`): "You MUST NOT approve or merge the PR. Your scope is limited to:
  code changes, comment replies, thread resolution, and re-requesting review" — FR-006
  - Depends on: T008

---

## Phase 5: User Story 5 — Cycle Limit & Infinite Loop Prevention (P1)

- [ ] T029 [US5] Verify the deduplication guard in dispatch-decision step (`.github/workflows/ai-pr-loop.yml`) enforces the 3-per-SHA limit: when count reaches 3, no further dispatches for that SHA
  and a "human intervention required" status is set on the repair comment (FR-007, SC-004)
  - Depends on: T003
- [ ] T061 [US5] Verify the deduplication guard increments the dispatch count and still dispatches when count is below the 3-per-SHA limit (FR-007, happy-path)
  - Depends on: T003
- [ ] T030 [US5] Verify the `agentic-repair` job's `timeout-minutes: 15` is correctly set in `.github/workflows/ai-pr-loop.yml` (FR-012). Add the failure handling step to detect timeout and PATCH the
  repair comment with "timed out — human intervention required"
  - Depends on: T011, T025
- [ ] T062 [US5] Verify the `agentic-repair` job has `timeout-minutes: 15` set in its job definition in `.github/workflows/ai-pr-loop.yml` (FR-012, happy-path)
  - Depends on: T011
- [ ] T056 [US5] Verify the dispatch-decision step only runs when `steps.guards.outputs.should_proceed == 'true'`, confirming the existing 50-cycle outer loop limit is respected (FR-011, happy-path)
  - Depends on: T006

---

## Phase 6: User Story 2 — Automated CI Failure Repair (P2)

### CI Log Retrieval

- [ ] T031 [US2] Add CI log retrieval step in the `agentic-repair` job (`.github/workflows/ai-pr-loop.yml`): use `gh api` to list check runs for head SHA, filter to failed checks (excluding `AI PR
  Loop` and `Generate lint fix patch`), get workflow run ID for each, use `gh run view <run_id> --log-failed` to get failure logs, truncate to last 200 lines per check (FR-002)
  - Depends on: T020
- [ ] T032 [US2] Add CI failure context injection into the prompt rendering step (`.github/workflows/ai-pr-loop.yml`): append `## CI Failure Context` section to the rendered prompt with check name,
  conclusion, and log excerpt for each failing check
  - Depends on: T021, T031

### CI-Safe Prompt — CI Failure Instructions

- [ ] T033 [US2] Add CI failure repair instructions to `.github/prompts/agdt.address-copilot-review.ci-repair.prompt.md`: parse failure messages, apply `ruff check --fix .` and `ruff format .` for
  lint failures, read test failures and fix code (using only pinned trusted tooling per SEC-003)
  - Depends on: T008

### Dispatch Decision — CI Failure Detection

- [ ] T034 [US2] Enhance the dispatch-decision step in `.github/workflows/ai-pr-loop.yml` to handle the `workflow_run` trigger path for CI failures: poll all required check suites via `gh api`
  check-suites endpoint to confirm terminal state before dispatching. Wait with bounded timeout if any required check is still `in_progress` or `queued`. Only dispatch when ALL required checks have
  completed AND at least one has `conclusion: failure` (FR-002 deterministic decision)
  - Depends on: T002
- [ ] T057 [US2] Verify CI failure detection: dispatch-decision step polls all required check suites to terminal state and sets `repair_needed=true`, `repair_type='ci'` when at least one has
  `conclusion: failure` (FR-002, happy-path)
  - Depends on: T034

---

## Phase 7: User Story 3 — Combined Review + CI Failure Handling (P2)

- [ ] T035 [US3] Ensure the dispatch-decision step in `.github/workflows/ai-pr-loop.yml` sets `repair_type: 'both'` when both `has_comments == 'true'` AND `has_failed_checks == 'true'`, and that the
  prompt rendering step injects both review URL and CI failure context
  - Depends on: T005, T021, T032
- [ ] T036 [US3] Add combined repair instructions to `.github/prompts/agdt.address-copilot-review.ci-repair.prompt.md`: address review comments first, then apply lint fixes, push once. Note that
  verification is delegated to the subsequent CI run
  - Depends on: T033

---

## Phase 8: User Story 6 — Observability & Auditability (P3)

- [ ] T037 [P] [US6] Enhance the repair comment body format in the dispatch-decision step (`.github/workflows/ai-pr-loop.yml`) to include structured metadata: repair type, trigger event, cycle count,
  dispatch count for this SHA, and a deep link to the workflow run with step-level anchor
  - Depends on: T003
- [ ] T038 [P] [US6] Add `core.notice()` and `core.warning()` workflow run annotations in the dispatch-decision step and repair job steps (`.github/workflows/ai-pr-loop.yml`) for key decision points:
  dispatch decision rationale, dedup guard state (current count, limit), PR state validation results
  - Depends on: T002, T011
- [ ] T039 [US6] Add commit message instruction to `.github/prompts/agdt.address-copilot-review.ci-repair.prompt.md`: instruct the agent to include `[ai-repair]` in the commit body so repair commits
  are identifiable in git log
  - Depends on: T008
- [ ] T040 [US6] Enhance the completion handling step in `.github/workflows/ai-pr-loop.yml` to include outcome summary in the PATCH-ed repair comment: comments addressed (count), threads resolved
  (count), commit SHA (if pushed), CI failures fixed (if CI repair), duration, Copilot session log link
  - Depends on: T025

---

## Phase 9: Polish & Cross-Cutting

- [ ] T041 Update the workflow header and security rationale in `.github/workflows/ai-pr-loop.yml` to document the new behavior: direct PR checkout as data-only (`persist-credentials: false`) for code
  edits alongside the trusted `main` checkout for prompts/instructions. Replace the statement about "PR branch is fetched only to apply a patch artifact" with accurate documentation of both checkout
  paths
  - Depends on: T013, T014
- [ ] T042 Confirm the `agentic-repair` job's concurrency model in `.github/workflows/ai-pr-loop.yml` prevents multiple repair jobs from running simultaneously for the same PR (NFR-005): confirm the
  workflow-level `concurrency` group (keyed by PR number, matching the existing `ai-pr-loop` job group) applies to both jobs, and `cancel-in-progress: false` is set
  - Depends on: T011
- [ ] T043 [P] Manual test: deduplication guard — trigger repair 3 times on same SHA, verify 4th dispatch is blocked with "human intervention required" comment update (FR-007)
  - Depends on: T029
- [ ] T044 [P] Manual test: privileged path guard — create a PR modifying `.github/workflows/test.yml`, verify repair is NOT dispatched (FR-010)
  - Depends on: T002
- [ ] T045 [P] Manual test: fork PR guard — verify repair is NOT dispatched for fork PRs (FR-013)
  - Depends on: T002
- [ ] T046 [P] Manual test: timeout handling — verify the 15-minute timeout produces a clear failure comment on the PR (FR-012)
  - Depends on: T030
- [ ] T047 [P] Manual test: partial success — create a PR where some comments are addressable and some are not, verify partial fixes are pushed and appropriate replies posted (FR-015)
  - Depends on: T025
- [ ] T048 Manual test: end-to-end review comment repair — create a test PR with intentional issues, trigger Copilot review, observe full dispatch → repair → push → re-review → merge cycle
  (FR-001, FR-009)
  - Depends on: T026
- [ ] T049 [P] Manual test: end-to-end CI failure repair — create a test PR with ruff violations, observe dispatch → repair → push → CI passes (FR-002)
  - Depends on: T031, T033
- [ ] T050 Manual test: combined review + CI repair — create a PR with both review comments and lint failures, verify both are handled in one pass (FR-001, FR-002, FR-015)
  - Depends on: T035, T036
- [ ] T058 [P] Manual test: label guard — create a PR with the `ai-pr-loop-ignore` label, verify repair is NOT dispatched (FR-014, happy-path)
  - Depends on: T002

---

## Dependency Summary

| Task | Depends On |
|---|---|
| T002 | — |
| T003 | T002 |
| T004 | T002 |
| T005 | T002, T003, T004 |
| T006 | T002 |
| T008 | — |
| T009 | T008 |
| T010 | — |
| T011 | T005 |
| T012 | T011 |
| T013 | T011 |
| T014 | T011 |
| T015 | T014 |
| T016 | T011 |
| T017 | T001, T016 |
| T018 | T016 |
| T019 | T017 |
| T020 | T015 |
| T021 | T008, T013, T020 |
| T022 | T008 |
| T023 | T011, T003 |
| T024 | T019, T021 |
| T025 | T024 |
| T026 | T025 |
| T027 | T025 |
| T028 | T008 |
| T029 | T003 |
| T030 | T011, T025 |
| T031 | T020 |
| T032 | T021, T031 |
| T033 | T008 |
| T034 | T002 |
| T035 | T005, T021, T032 |
| T036 | T033 |
| T037 | T003 |
| T038 | T002, T011 |
| T039 | T008 |
| T040 | T025 |
| T041 | T013, T014 |
| T042 | T011 |
| T051 | T002, T005 |
| T052 | T011 |
| T053 | T012 |
| T054 | T023, T025 |
| T055 | T026 |
| T056 | T006 |
| T057 | T034 |
| T058 | T002 |
| T059 | T013, T017 |
| T060 | T027 |
| T061 | T003 |
| T062 | T011 |

## FR Coverage Matrix

| FR | Tasks |
|---|---|
| FR-001 | T002, T007, T048, T050, T051 (detect actionable Copilot review comments and dispatch) |
| FR-002 | T031, T032, T034, T049, T050, T057 |
| FR-003 | T011, T052 |
| FR-004 | T012, T053 (PAT authentication via `secrets.COPILOT_GITHUB_TOKEN`) |
| FR-005 | T013, T017, T019, T059 |
| FR-006 | T027, T028, T060 |
| FR-007 | T003, T029, T043, T061 |
| FR-008 | T023, T025, T054 |
| FR-009 | T007, T026, T048, T055 (re-request Copilot review after pushing fixes) |
| FR-010 | T002, T004, T044 |
| FR-011 | T006, T056 (dispatch-decision respects existing 50-cycle outer loop limit) |
| FR-012 | T011, T030, T046, T062 |
| FR-013 | T002, T045 |
| FR-014 | T002, T058 |
| FR-015 | T047, T050 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
