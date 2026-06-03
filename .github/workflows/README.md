# GitHub Workflows

This directory contains GitHub Actions workflows for the agentic-devtools project.

## Workflows

### ai-pr-loop.yml

**Automated AI PR Fix → Review → Merge Loop**

- Runs on: `workflow_dispatch` only (scheduler-driven)
- Purpose: Fully autonomous PR handling — inspect failed checks and review comments, repair issues, approve, and merge

**How it works**:

1. **Scheduler-only trigger**: The workflow is invoked exclusively via `workflow_dispatch` by the
   agent-session-monitor scheduler, which selects exactly one PR per invocation
2. **Exclusion Labels**: `ai-pr-loop-ignore` skips entirely; missing `ai-auto-merge-allowed` prevents merge but allows fixes/approval
3. **Repair dispatch**: Uses failed PR checks and Copilot review state to decide when to request fixes
4. **Amend & Push**: Amends fixes into the last commit with `--force-with-lease`
5. **Copilot Review Handling**: Detects outstanding Copilot review comments and blocks merge until resolved
6. **Approve & Merge**: When all checks pass, Copilot review is clean, and no outstanding comments, approves and squash-merges
7. **Stale Review Re-request**: Re-requests Copilot review if >30 minutes stale
8. **Cycle Tracking**: Maximum 50 outer cycles before posting exhaustion notice
9. **Continuous loop**: After finishing (even on failure), dispatches `ai-pr-loop-redispatch.yml`
   to keep the loop going without waiting for a scheduler

**Post-repair squash flow** (handled by Pipeline v2):

After Copilot pushes a repair commit and CI passes, the squash is handled inline by the Pipeline v2
`SquashAction` which evaluates conditions each time `ai-pr-loop` runs — no external scheduler needed.

**Required Permissions**:

- `contents: write`
- `pull-requests: write`
- `issues: write`
- `actions: write`
- `checks: read`

**Concurrency**: Single instance per PR (`ai-pr-loop-{pr_number}`), non-cancelling

### agent-session-monitor.yml

**PR Scheduler — Oldest-Eligible PR Dispatch**

- Runs on: `workflow_dispatch` only (no cron; driven continuously by `ai-pr-loop-redispatch.yml`,
  and cold-started by `pr-activity-dispatch.yml` on PR events)
- Purpose: Selects the oldest eligible open PR and dispatches `ai-pr-loop.yml` for it.
  At most one PR is processed per invocation.

**Selection logic**:

1. Lists open PRs ordered by creation date ascending (oldest first)
2. Skips fork PRs
3. Skips PRs with `ai-pr-loop-ignore` exclusion label
4. Detects human-blocked PRs (merge-ready but missing `ai-auto-merge-allowed`) and skips them
5. Dispatches `ai-pr-loop.yml` for the first AI-actionable PR found
6. Exits cleanly if no eligible PR exists

**Human-blocked definition**: A PR is human-blocked when it has passing CI, an approval,
but does NOT have the `ai-auto-merge-allowed` label. Such PRs are skipped so they do not
stall the queue.

**Required Permissions**:

- `contents: read`
- `pull-requests: write`
- `actions: write`
- `issues: write`

**Required Secrets**: `AGDT_PR_APPROVER_PAT`

### ai-pr-loop-redispatch.yml

**AI PR Loop Redispatch — Smart Continuous Scheduling**

- Runs on: `workflow_dispatch` only (dispatched by `ai-pr-loop.yml` after each run)
- Purpose: Keeps the AI PR processing loop running continuously without a cron scheduler.
  Calculates the safe time to dispatch `agent-session-monitor.yml` (respecting the 60 s cooldown
  enforced by `pr-activity-dispatch.yml`) and sleeps until then.

**Loop lifecycle**:

```text
pr-activity-dispatch (cold-start on PR events)
  → agent-session-monitor (selects oldest eligible PR)
    → ai-pr-loop (processes the PR: fix / review / merge)
      → ai-pr-loop-redispatch (checks stop conditions → sleeps → dispatches)
        → agent-session-monitor → ...
```

**Stop conditions** (loop breaks if either is true):

1. **No eligible open PRs** — no open PRs outside the `ai-pr-loop-ignore` label exist. The loop
   breaks cleanly; `pr-activity-dispatch` will restart it when a new PR is opened or updated.
2. **No merges to main in 24+ hours** — likely stuck PRs needing human intervention.

**Loop restart**: `pr-activity-dispatch` fires on `opened`, `synchronize`, `reopened`, `labeled`,
`unlabeled`, `ready_for_review`, `review_requested`, and `closed` PR events.

**Sleep calculation**: Queries the last `agent-session-monitor` run's `updated_at` timestamp
and sleeps until `last_completed + 65s` (5 s margin over `pr-activity-dispatch`'s 60 s cooldown).

**Required Permissions**:

- `actions: write`
- `pull-requests: read`
- `contents: read`

**Required Secrets**: `AGDT_PR_APPROVER_PAT`

**Concurrency**: `ai-pr-loop-redispatch` group with `cancel-in-progress: true`
(only the latest redispatch matters)

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

**SpecKit Issue Trigger — Thin Dispatcher (Phase 1)**

- Runs on:
  - Issues labeled event (when `speckit` or configured label is added)
  - Manual workflow dispatch
- Purpose: Dispatches Phase 1 (Specify) to the unified `speckit-phase-progression.yml` workflow via `workflow_dispatch` with `phase=1`
- Does NOT perform generation, commit, or PR creation directly — delegates all logic to the progression workflow
- Retains per-issue concurrency group, processing label management, and failure handling

### speckit-phase-progression.yml

**SpecKit Phase Progression (Phases 1–5)**

- Runs on:
  - Pull request closed (merged) events with `speckit:phase-N` labels
  - Manual `workflow_dispatch` with inputs:
    - `issue_number` (required): The GitHub issue number to progress
    - `phase` (required): The phase to generate (1–5)
- Purpose: Unified workflow that handles all SpecKit pipeline phases.
  Generates phase artifacts and creates PRs using human-identity tokens
  (`SPECKIT_PR_TOKEN` or `COPILOT_GITHUB_TOKEN`).
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
