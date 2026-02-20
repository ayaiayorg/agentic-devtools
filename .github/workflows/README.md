# GitHub Workflows

This directory contains GitHub Actions workflows for the agentic-devtools project.

## Workflows

### auto-fix-on-failure.yml

**Automated PR Check Failure Fix**

- Runs on: `workflow_run` completion for test and lint workflows
- Trigger condition: Only when workflow fails and was triggered by a pull request
- Purpose: Automatically tags `@copilot` to analyze and fix failing PR checks
- Retry Limit: Calculates max retries as `number_of_failing_jobs × 3`
- Loop Prevention: Tracks attempts using HTML comments, stops at max retry limit

**How it works**:

1. **Failure Detection**: Triggered when "Python Tests and Linting" or "Lint" workflows fail on a PR
2. **PR Lookup**: Finds the associated pull request from the workflow run's head branch
3. **Retry Tracking**:
   - On first attempt: Counts failed jobs, calculates max retries (e.g., 2 failed jobs = 6 max retries)
   - Stores max retry in first comment: `<!-- auto-fix-max: 6 -->`
   - Marks each attempt with: `<!-- auto-fix-comment -->`
4. **Auto-Fix Request**: Posts comment tagging `@copilot` with failure details and job links
5. **Limit Enforcement**: When max retries reached, posts a comment requesting human review

**Required Permissions**:

- `contents: read`
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

### test.yml

**Python Tests and Linting**

- Runs on: Pull requests and pushes to main
- Tests Python versions: 3.11, 3.12
- Includes: pytest with coverage, black, isort, mypy, ruff
- Purpose: Ensures code quality and test coverage

### lint.yml

**Markdown Linting**

- Runs on: Pull requests and pushes to main
- Tool: markdownlint-cli2
- Purpose: Ensures consistent markdown formatting across documentation
- Scope: All `*.md` files in the repository

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
