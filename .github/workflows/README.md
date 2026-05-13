# GitHub Workflows

This directory contains GitHub Actions workflows for the agentic-devtools project.

## Workflows

### ai-pr-loop.yml

**Automated AI PR Fix → Review → Merge Loop**

- Runs on: `workflow_run` completion of "AI PR Loop Lint" AND `pull_request_review` (Copilot)
- Purpose: Fully autonomous PR handling — fix lint failures, detect review comments, approve, and merge
- Supersedes the former `auto-fix-on-failure.yml`

**How it works**:

1. **Trigger Guards**: Prevents redundant runs — if triggered by Copilot review but checks are still pending,
   polls every 30 seconds for up to 10 minutes (skips on timeout);
   if a Copilot review on the head commit has `CHANGES_REQUESTED` state, blocks merge until resolved
2. **Dispatch Pre-Check (FR-009)**: When triggered by `workflow_run`, checks the lint run's conclusion —
   if `action_required` (pending workflow approval) or `null` (not yet finalized), skips dispatch to avoid
   wasting resources; the `workflow-approval-monitor.yml` handles approval separately
3. **Exclusion Labels**: `ai-pr-loop-ignore` skips entirely; `do-not-auto-merge` prevents merge but allows fixes/approval
4. **Layer 1 — Deterministic fixers**: Downloads and applies lint patches produced by the unprivileged "AI PR Loop Lint" workflow
5. **Amend & Push**: Amends fixes into the last commit with `--force-with-lease`
6. **Copilot Review Handling**: Detects outstanding Copilot review comments and blocks merge until resolved
7. **Approve & Merge**: When all checks pass, Copilot review is clean, and no outstanding comments, approves and squash-merges
8. **Stale Review Re-request**: Re-requests Copilot review if >30 minutes stale
9. **Cycle Tracking**: Maximum 50 outer cycles before posting exhaustion notice
10. **Fallback Path (FR-006)**: When triggered via `pull_request_review` with a workflow-approval-fallback
    marker, logs a breadcrumb indicating the lint workflow is in `action_required` state

**Required Permissions**:

- `contents: write`
- `pull-requests: write`
- `issues: write`
- `actions: write`
- `checks: read`

**Concurrency**: Single instance per PR (`ai-pr-loop-{pr_number}`), non-cancelling

### ai-pr-loop-lint.yml

**Unprivileged Lint Patch Generator**

- Runs on: `pull_request` events (`synchronize`, `opened`, `reopened`)
- Purpose: Runs deterministic auto-fixers (ruff lint/format, markdownlint) on PR code in a
  read-only sandbox, producing a patch artifact for the privileged "AI PR Loop" workflow to apply.
  This trust-boundary split ensures untrusted PR code never executes with write permissions or secrets.
- Artifact: `ai-pr-loop-lint-patch` (contains `lint-fixes.patch` + PR metadata; retention: 1 day)

**Required Permissions** (read-only):

- `contents: read`
- `actions: read`

**Concurrency**: Single instance per PR (`ai-pr-loop-lint-{pr_number}`), cancel-in-progress

**Workflow Approval Behavior**: When triggered by PRs from bot accounts that are repository
collaborators (e.g., `copilot-swe-agent[bot]`, `github-actions[bot]`), this workflow runs
immediately without requiring manual approval. For non-collaborator bot accounts, the workflow
enters `action_required` state and is automatically approved by `workflow-approval-monitor.yml`.

### workflow-approval-monitor.yml

**Programmatic Workflow Approval for Trusted Bots**

- Runs on: `schedule` (every 5 minutes) and `workflow_dispatch` (manual)
- Purpose: Automatically approves workflow runs that are stuck in `action_required` state
  for PRs authored by trusted bot accounts, eliminating manual intervention in the autonomous
  AI PR loop

**How it works**:

1. Loads the trusted bot allow-list from `.github/ai-pr-loop-config.json`
2. Lists recent `ai-pr-loop-lint.yml` runs with `conclusion=action_required`
3. Filters to runs older than 2-minute threshold (FR-004)
4. Validates each run's associated PR author is in the trusted list and PR is same-repo (not fork)
5. Approves eligible runs via `POST /repos/{owner}/{repo}/actions/runs/{run_id}/approve`
6. Emits structured JSON audit log entries for each action (success/failure/skip)
7. Tracks retry count per (pr_number, head_sha) via PR comment markers — stops after 3 failures
8. After retry limit: posts PR comment with manual resolution instructions
9. Graceful degradation: posts synthetic review to trigger `pull_request_review` fallback path

**Config file**: `.github/ai-pr-loop-config.json`

```json
{
  "trusted_bot_accounts": ["copilot-swe-agent[bot]", "github-actions[bot]"],
  "lookback_hours": 48
}
```

- `trusted_bot_accounts` — GitHub usernames of bots eligible for automatic approval
- `lookback_hours` — How far back (in hours) to scan for stuck runs (default: 48)

**Required Permissions**:

- `actions: read` (list/get workflow runs)
- `pull-requests: read` (read PR metadata)
- `issues: write` (post PR comments)
- `contents: read` (read config file)

**Required Secrets**:

- `COPILOT_GITHUB_TOKEN` — PAT with Actions write permission (fine-grained: "Actions: Read and write";
  classic: `workflow` scope). Used for the approve API call per FR-003/NFR-003.
- `SPECKIT_PR_TOKEN` — Used for synthetic review fallback (optional; graceful degradation only)

**Concurrency**: Single instance (`workflow-approval-monitor`), queued (no cancel-in-progress)

### Fork Pull Request Workflows Policy

To eliminate the approval gate for trusted bot accounts (FR-001/FR-002), configure the
repository settings:

1. Go to **Settings → Actions → General → Fork pull request workflows**
2. Under "Run workflows from fork pull requests", ensure trusted bot accounts are
   added as repository collaborators with at least `read` access
3. Bot accounts with collaborator status will have their PRs' workflows run automatically
   without requiring manual approval

**Note**: GitHub App bot accounts (e.g., `copilot-swe-agent[bot]`) may not be addable as
traditional collaborators. In this case, the `workflow-approval-monitor.yml` serves as the
automatic fallback to programmatically approve their workflow runs.

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

Reviews with this marker from trusted users (`acmarsnik`) are recognized by `copilot-review-gate.yml`
and `ai-pr-loop.yml` as equivalent to official `copilot-pull-request-reviewer[bot]` reviews:

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

### test.yml

**Python Tests and Linting**

- Runs on: Pull requests and pushes to main
- Tests Python version: 3.12 (single version)
- Purpose: Ensures code quality and test coverage

**Jobs**:

#### `detect-changes`

Detects which source modules changed using `dorny/paths-filter@v3`. Outputs a flag per module and a
`has_modules` flag (true if any module changed). Also detects `config` changes
(`pyproject.toml`, `conftest.py`, etc.).

#### `test-smart` (PR only, when modules changed)

Runs on pull requests when at least one Python module changed. Builds the pytest command dynamically:

- Collects test paths for changed modules (only paths that exist on disk)
- Collects `--cov=<source>` flags for changed modules
- Runs `pytest` with `--cov-fail-under=100 --override-ini="addopts="` scoped to only the changed modules
- Also validates the 1:1:1 test structure

**Per-module 100% coverage**: If a PR touches `cli/git/`, it must have 100% coverage on `cli/git/` source files.

#### `test-full` (push to main, or config files changed)

Runs the complete test suite when pushing to `main` or when config files
(`pyproject.toml`, `tests/conftest.py`, etc.) change:

- `pytest --cov=agentic_devtools --cov-report=term-missing --cov-fail-under=100 --ignore=tests/workflows`
- E2E smoke tests
- Uploads coverage to Codecov

#### `test-skipped` (PR only, no Python changes)

Placeholder job that succeeds when no Python files changed (docs-only PRs, etc.).
Ensures required status checks are satisfied without blocking merges.

#### `lint` (informational, non-blocking)

Runs `black`, `isort`, `mypy`, and `ruff` checks when Python files changed or on push to main.
Uses `continue-on-error: true` — failures are informational only.

#### `tests-gate` (required status check)

Gate job (`Tests ✅`) that always runs after `test-smart`, `test-full`, and `test-skipped`.
Fails if any downstream test job failed. This is the single required status check for branch protection.

### lint.yml

**Markdown Linting**

- Runs on:
  - Pushes to `main` (always lint on merge)
  - Pull requests (always triggered; internal change detection skips the lint job when irrelevant)
- Tool: markdownlint-cli2
- Purpose: Ensures consistent markdown formatting across documentation
- Scope: All `*.md` files in the repository

**Jobs**:

- `changes`: Detects if markdown files changed using `dorny/paths-filter@v3`
- `markdownlint`: Runs markdownlint when markdown files changed (or on push to main)
- `markdownlint-skipped`: Placeholder that succeeds when no markdown files changed
  (used to satisfy required status checks when no markdown files are affected)
- `lint-gate`: Gate job (`Markdown Lint ✅`) — always runs, fails if any downstream job failed

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
