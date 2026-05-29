# GitHub Workflows

This directory contains GitHub Actions workflows for the agentic-devtools project.

## Workflows

### ai-pr-loop.yml

**Automated AI PR Fix → Review → Merge Loop**

- Runs on: `pull_request` (`opened`, `reopened`, `synchronize`), `pull_request_review` (Copilot),
  `issue_comment` (Copilot completion — exits immediately, no squash), `workflow_run` (CI completion),
  and `workflow_dispatch` (squash-wait-scheduler re-invocations)
- Purpose: Fully autonomous PR handling — inspect failed checks and review comments, repair issues, approve, and merge

**How it works**:

1. **Safe direct trigger**: Even on `pull_request`, the workflow only checks out `main` and installs
   `agentic-devtools` from PyPI, so it does not execute untrusted PR code
2. **Trigger Guards**: Prevents redundant runs — if triggered by Copilot review but checks are still pending,
   polls every 30 seconds for up to 10 minutes (skips on timeout);
   if a Copilot review on the head commit has `CHANGES_REQUESTED` state, blocks merge until resolved
3. **Exclusion Labels**: `ai-pr-loop-ignore` skips entirely; missing `ai-auto-merge-allowed` prevents merge but allows fixes/approval
4. **Repair dispatch**: Uses failed PR checks and Copilot review state to decide when to request fixes
5. **Amend & Push**: Amends fixes into the last commit with `--force-with-lease`
6. **Copilot Review Handling**: Detects outstanding Copilot review comments and blocks merge until resolved
7. **Approve & Merge**: When all checks pass, Copilot review is clean, and no outstanding comments, approves and squash-merges
8. **Stale Review Re-request**: Re-requests Copilot review if >30 minutes stale
9. **Cycle Tracking**: Maximum 50 outer cycles before posting exhaustion notice

**Post-repair squash flow** (new, replaces `issue_comment`-triggered squash):

After Copilot pushes a repair commit and CI passes, the squash is deferred until a terminal
`copilot_work_finished` / `copilot_work_finished_failure` event is detected (via the GitHub Issues
Events API). A `<!-- squash-wait` marker comment tracks state on the PR. The
`squash-wait-scheduler.yml` workflow re-invokes ai-pr-loop every 5 minutes for any PR with an
active marker, up to 24 attempts (~120 minutes).

`issue_comment` events from Copilot are now ignored for squash purposes — they return immediately
with no action. The squash always happens via `workflow_run` or `workflow_dispatch` triggers.

**Required Permissions**:

- `contents: write`
- `pull-requests: write`
- `issues: write`
- `actions: read`
- `checks: read`

**Concurrency**: Single instance per PR (`ai-pr-loop-{pr_number}`), non-cancelling

### squash-wait-scheduler.yml

**Post-Repair Squash Wait Scheduler**

- Runs on: `schedule` (every 5 minutes, `*/5 * * * *`) and `workflow_dispatch` (manual)
- Purpose: Finds open PRs with an active `<!-- squash-wait` marker comment and triggers
  `workflow_dispatch` on `ai-pr-loop.yml` for each one, so the squash-wait state machine
  can check the GitHub Issues Events API and proceed when ready

**How it works**:

1. Uses a single GitHub Search API query to find open PRs that contain an active `<!-- squash-wait` marker comment
2. Parses the matching PR numbers from search results (no per-PR comment scan loop)
3. Triggers `gh workflow run ai-pr-loop.yml` with `pr_number` and `trigger_reason=squash_wait_scheduler` for each match
4. The ai-pr-loop reads the marker and makes its decision (wait / squash) via Python — zero decision logic in the YAML

**Squash-wait marker format**:

```text
<!-- squash-wait
sha=<full-head-sha>
attempt=<N>
head_pushed_at=<ISO8601 UTC timestamp>
ci_passed=true
copilot_session_terminal=<true|false>
copilot_session_outcome=<pending|success|failure>
squash_done=false
-->
Squash wait in progress for PR #<N> — last checked <ISO8601 timestamp>
```

**Field semantics**:

- `sha` — head SHA this wait is tracking; SHA mismatch → treated as first visit (marker reset)
- `attempt` — incremented each cron tick; at attempt 24 (~120 min) squash is forced if no terminal event
- `head_pushed_at` — ISO 8601 UTC timestamp used as context reference
- `ci_passed=true` — always true when the marker is first written (CI passing is the write precondition)
- `copilot_session_terminal` — set to `true` once a terminal event (`copilot_work_finished` or
  `copilot_work_finished_failure`) is found; never re-checked after that
- `copilot_session_outcome` — `pending` until terminal; then `success` or `failure`
- `squash_done` — set to `true` and marker replaced with a completion note after squash executes

**Decision table**:

| State | Per-cron-tick action | When to squash |
|---|---|---|
| `outcome=pending` | Query events API; update marker if terminal found | Immediately on `copilot_work_finished` |
| `outcome=success` | — | Already squashed |
| `outcome=failure` | Wait, no API calls | Attempt 24 (~120 min from push), with recovery comment |
| `outcome=pending` + attempt 24 | Timeout fallback | Attempt 24, with timeout comment |

**Required Permissions**:

- `contents: read`
- `pull-requests: read`
- `actions: write`

**Required Secrets**: `AGDT_PR_APPROVER_PAT`

### synthetic-copilot-review.yml

**Synthetic Copilot Review Fallback**

- Runs on: `schedule` (every 30 minutes) and `workflow_dispatch` (manual)
- Purpose: Detects PRs stuck waiting for Copilot Code Review (CCR) and posts synthetic reviews
  to unblock them when CCR completes agent sessions but fails to post a review

**How it works**:

1. Lists open PRs targeting `main` with a pending Copilot review request older than 1 hour
   (determined from the `review_requested` timeline event timestamp, with fallback to `pr.updated_at`)
2. For each stuck PR, attempts to parse agent-task logs for intended comments (`store_comment` minus `remove_comment`)
3. Posts a synthetic review based on parse results:
   - **Parse success, comments found**: Posts with reconstructed inline comments
   - **Parse success, no comments**: Posts a clean "no comments" review (`COMMENT` event)
   - **Parse failure**: Posts `REQUEST_CHANGES` with `parse_failed=true` marker to block auto-merge
   - **Inline posting failure**: Falls back to summary-only review with `inline_post_failed=true` marker
4. Skips PRs that already have a real Copilot review or existing synthetic review on the current head commit

**Synthetic Review Marker**: `<!-- synthetic-copilot-review -->`

**Machine-readable metadata** (included in all synthetic review bodies):
`<!-- intended_comments=N inline_posted=N parse_failed=true/false [inline_post_failed=true] -->`

Reviews with this marker from trusted users (`acmarsnik`) are recognized by
`copilot-review-gate.yml` and `ai-pr-loop.yml` as equivalent to official
`copilot-pull-request-reviewer[bot]` reviews:

- Synthetic review with 0 inline comments and `parse_failed=false` → gate passes (clean review)
- Synthetic review with >0 inline comments → gate fails, triggers review addresser flow
- Synthetic review with `parse_failed=true` → gate fails (inconclusive, manual review required)
- Synthetic review with `intended_comments>0` but `inline_posted=0` → gate/merge blocked

**Required Permissions**:

- `contents: read`
- `issues: read`
- `pull-requests: write`

**Required Secrets**: `SPECKIT_PR_TOKEN` (PAT owned by `acmarsnik` with `repo` scope)

### speckit-issue-trigger.yml

**SpecKit Issue to Specification Automation (Phase 1 — Specify)**

- Runs on:
  - Issues labeled event (when `speckit` or configured label is added)
  - Manual workflow dispatch
- Purpose: Generates the initial feature specification (`spec.md`) from a GitHub issue — Phase 1 of the SpecKit per-phase pipeline
- Outputs: Creates Phase 1 branch (`speckit/<issue>/phase-1-specify`), spec file, and pull request labeled `speckit:phase-1`
- Scripts: Uses helper scripts in `.github/scripts/speckit-trigger/`
- **Sequence Diagram**: See
  [Workflow Sequence Diagram](../../specs/002-github-action-speckit-trigger/workflow-sequence-diagram.md)
  for the original workflow design
  (note: the diagram predates the per-phase PR progression and may not reflect the current split pipeline)

### speckit-phase-progression.yml

**SpecKit Phase Progression (Phases 2–5)**

- Runs on:
  - Pull request closed (merged) events with `speckit:phase-N` labels
  - Manual `workflow_dispatch` with inputs:
    - `issue_number` (required): The GitHub issue number to progress
    - `phase` (required): The phase to generate (2–5)
- Purpose: Automatically progresses the SpecKit pipeline when a phase PR is merged.
  Generates the next phase's artifacts and creates a new PR.
  The `workflow_dispatch` trigger allows operators to recover or retry phases
  when the merge trigger fails or a PR is missing the `speckit:phase-N` label.
- Phase flow: specify → clarify → plan → tasks → analyze
- Supports auto-merge for trusted phases via `SPECKIT_AUTO_MERGE_PHASES` repository variable
- Scripts: Uses helper scripts in `.github/scripts/speckit-trigger/`

### workflow-tests.yml

**Workflow Integration Tests**

- Runs on:
  - Pull requests to `main` (always triggered; internal change detection skips the test job when irrelevant)
  - Pushes to `main` (always)
- Tests Python version: 3.12 (single version)
- Purpose: Runs the workflow integration tests in `tests/workflows/` as a dedicated pipeline,
  separate from the unit tests and coverage enforcement in `test.yml`

**Jobs**:

- `changes`: Detects if workflow-related files changed using `dorny/paths-filter@v3`
  (paths: `agentic_devtools/cli/workflows/**`, `tests/workflows/**`, `agentic_devtools/prompts/**`,
  `agentic_devtools/state.py`, `agentic_devtools/background_tasks.py`, `pyproject.toml`)
- `workflow-tests`: Runs workflow integration tests when workflow files changed (or on push to main)
- `workflow-tests-skipped`: Placeholder that succeeds when no workflow files changed
  (used to satisfy required status checks when workflow-related files are not affected)
- `workflow-tests-gate`: Gate job (`Workflow Tests ✅`) — always runs, fails if any downstream job failed

### pr-targeted-checks.yml

**PR Targeted Checks**

- Runs on: Pull requests to `main`
- Purpose: Fast, scoped checks on changed files only (~30s)

**Checks performed** (only on changed files):

- `ruff check` (lint) on changed `.py` files
- `ruff format --check` on changed `.py` files
- `markdownlint-cli2` on changed `.md` files
- Per-file 100% branch coverage for changed `agentic_devtools/**/*.py` files
- `mypy` on changed `.py` files
- `validate_test_structure.py` if test files changed

**Jobs**:

- `targeted-checks`: Runs `scripts/targeted-checks.sh` with the list of changed files
- `targeted-checks-gate`: Gate job (`Targeted Checks ✅`) — required status check

### copilot-review-gate.yml

**Copilot Review Gate**

- Runs on: Pull requests to `main` (`opened`, `synchronize`, `reopened`)
- Purpose: Enforces Copilot review freshness and cleanliness before merge

**Logic**:

- First checks for a trusted Copilot/synthetic review directly on HEAD
- If none exists on HEAD, finds the latest trusted prior review and compares SHA-256
  content hashes of `git diff origin/main...<reviewed_sha>` and
  `git diff origin/main...<head_sha>`
- If hashes match → review is still fresh (rebase/base-shift only) → passes
- If hashes differ → code changed since review → fails (needs re-review)
- If no trusted Copilot review exists yet → fails the gate (`No Copilot review yet`)

**Jobs**:

- `copilot-review-gate`: Validates review freshness and comment cleanliness
- Gate job name: `Copilot Review ✅` — required status check

### pr-smart-module-tests.yml

**PR Smart Module Tests**

- Runs on: `pull_request_review` (`submitted`) — filtered to Copilot approval
- Purpose: Runs scoped pytest with per-module 100% coverage after Copilot review approval

**Jobs**:

- `smart-module-tests`: Detects changed modules via `dorny/paths-filter`, runs scoped pytest
- `smart-module-tests-gate`: Gate job (`Smart Module Tests ✅`) — required status check

### post-merge-full-suite.yml

**Post-Merge Full Suite**

- Runs on: Push to `main` only
- Purpose: Integration safety net — runs the complete test suite post-merge

**Checks performed**:

- Full `pytest --cov=agentic_devtools --cov-fail-under=100`
- Workflow integration tests
- E2E smoke tests
- `ruff check .` + `ruff format --check .`
- `markdownlint-cli2 "**/*.md"`
- `mypy .` (informational)

**NOT a merge gate** — runs after merge as a quality signal.

### release.yml

**Automated Release Creation**

- Runs on:
  - Pushes to `main` affecting `agentic_devtools/**` or `pyproject.toml`
  - Manual workflow dispatch
- Purpose: Automatically create a new patch release tag and publish a GitHub release with generated notes
- Scripts: Uses helper scripts in `.github/workflows/scripts/` for next-version calculation and release existence checks
- **Required for automatic PyPI publishing**: `RELEASE_PAT` — a fine-grained PAT with `contents: write` permission
  (see [RELEASING.md](../../RELEASING.md#release_pat-requirement)); the workflow falls back to `GITHUB_TOKEN`
  but automatic publishing to PyPI will not trigger without it

> **Why a PAT?** GitHub does not fire the `release: published` event when a release is created with
> `GITHUB_TOKEN`. A PAT is required so that creating a release here automatically triggers
> `publish.yml` to build and publish the package to PyPI. Without `RELEASE_PAT`, publishing must be
> triggered manually.

## Release Workflow Details

The release workflow:

1. **Version Management**: Automatically increments version based on latest git tag, or reuses the
   latest tag when it exists without a corresponding release (for idempotent reruns)
2. **Duplicate Protection**: Skips execution when the next version release already exists
3. **Tag Creation**: Creates and pushes the new semantic version tag on the triggering commit
   (`github.sha` for push events, `main` HEAD for `workflow_dispatch`)
4. **GitHub Release**: Publishes a release for the new tag using GitHub-generated notes (`gh release create --generate-notes`)

### Release Scripts

Located in `.github/workflows/scripts/`:

- `get-next-version.sh`: Calculates next semantic version
- `check-release-exists.sh`: Prevents duplicate releases

## Spec-Driven Development (SDD)

This project follows the [Spec-Kit](https://github.com/github/spec-kit) methodology for Spec-Driven Development. The `.specify/` directory contains:

- `memory/constitution.md`: Project principles and governance
- `scripts/bash/` and `scripts/powershell/`: Helper scripts
- `templates/`: Feature specification templates
- `templates/commands/`: AI assistant command templates

These templates support the development process but are not release assets for the Python package workflow.
