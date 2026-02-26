# GitHub Workflows

This directory contains GitHub Actions workflows for the agentic-devtools project.

## Workflows

### auto-fix-on-failure.yml

**Automated PR Check Failure Fix**

- Runs on: `workflow_run` completion for test, workflow integration tests, and lint workflows
- Trigger condition: Only when workflow fails and was triggered by a pull request
- Purpose: Automatically applies `ruff` auto-fixes and pushes them to the PR branch
- Retry Limit: 3 Tier 1 (ruff) attempts per PR
- Loop Prevention: Tracks attempts using HTML comments, stops at max retry limit

**How it works**:

1. **Failure Detection**: Triggered when "Python Tests and Linting", "Workflow Integration Tests", or "Lint" workflows fail on a PR
2. **PR Lookup**: Finds the associated pull request from the workflow run's head branch
3. **Tier 1 — ruff auto-fix**: Runs `ruff check --fix` and `ruff format`, commits and pushes any changes
4. **Retry Tracking**: Marks each attempt with an HTML comment; stops after 3 attempts
5. **Exhaustion Notice**: Posts a human-intervention comment when all retries are used

**Required Permissions**:

- `contents: write`
- `issues: write`
- `pull-requests: write`

### speckit-issue-trigger.yml

**SpecKit Issue to Specification Automation**

- Runs on:
  - Issues labeled event (when `speckit` or configured label is added)
  - Manual workflow dispatch
- Purpose: Automatically generates feature specifications from GitHub issues following the Spec-Driven Development (SDD) pattern
- Outputs: Creates specification branch, files, and pull request
- Scripts: Uses helper scripts in `.github/scripts/speckit-trigger/`
- **Sequence Diagram**: See [Workflow Sequence Diagram](../../specs/002-github-action-speckit-trigger/workflow-sequence-diagram.md) for complete visual documentation of the workflow

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
  - Pushes to main affecting `.specify/memory/**`, `.specify/scripts/**`, `.specify/templates/**`, or `.github/workflows/**`
  - Manual workflow dispatch
- Purpose: Automatically creates releases with Spec-Driven Development (SDD) template packages
- Outputs: Creates release packages for multiple AI assistants (Claude, Copilot, Gemini, Cursor, etc.)
- Scripts: Uses helper scripts in `.github/workflows/scripts/`
- **Required for automatic PyPI publishing**: `RELEASE_PAT` — a fine-grained PAT with `contents: write` permission
  (see [RELEASING.md](../../RELEASING.md#release_pat-requirement)); the workflow falls back to `GITHUB_TOKEN`
  but automatic publishing to PyPI will not trigger without it

> **Why a PAT?** GitHub does not fire the `release: published` event when a release is created with
> `GITHUB_TOKEN`. A PAT is required so that creating a release here automatically triggers
> `publish.yml` to build and publish the package to PyPI. Without `RELEASE_PAT`, publishing must be
> triggered manually.

## Release Workflow Details

The release workflow:

1. **Version Management**: Automatically increments version based on latest git tag
2. **Package Creation**: Generates SDD template packages for different AI assistants:
   - Claude (`.claude/commands/`)
   - Copilot (`.github/agents/`)
   - Gemini (`.gemini/commands/`)
   - Cursor (`.cursor/commands/`)
   - And many others (OpenCode, Windsurf, Qwen, etc.)
3. **Release Notes**: Auto-generates release notes from git history
4. **GitHub Release**: Creates a GitHub release with all package variants
5. **Version Update**: Updates `pyproject.toml` with the new version

### Release Scripts

Located in `.github/workflows/scripts/`:

- `get-next-version.sh`: Calculates next semantic version
- `check-release-exists.sh`: Prevents duplicate releases
- `create-release-packages.sh`: Builds all SDD template packages
- `generate-release-notes.sh`: Creates release notes from commits
- `create-github-release.sh`: Publishes the GitHub release
- `update-version.sh`: Updates version in pyproject.toml

## Spec-Driven Development (SDD)

This project follows the [Spec-Kit](https://github.com/github/spec-kit) methodology for Spec-Driven Development. The `.specify/` directory contains:

- `memory/constitution.md`: Project principles and governance
- `scripts/bash/` and `scripts/powershell/`: Helper scripts
- `templates/`: Feature specification templates
- `templates/commands/`: AI assistant command templates

The release workflow packages these templates into formats compatible with different AI coding assistants.
