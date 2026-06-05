# Feature Specification: Adopt uv as pip replacement for faster CI installs

**Feature Branch**: `speckit/1754/phase-1-specify`
**Created**: 2026-06-03
**Status**: Draft
**Input**: GitHub Issue #1754 — Adopt uv as pip replacement for faster CI installs
**Source Issue**: #1754 (<https://github.com/ayaiayorg/agentic-devtools/issues/1754>)

## Problem Statement

CI workflows currently use `python -m pip install` to install `agentic-devtools` and its full dependency tree
(langgraph, azure SDKs, requests, and others). Python's dependency resolver is slow, adding significant overhead to
every workflow run. `uv` is a drop-in pip replacement written in Rust that provides 10-100× faster dependency
resolution and installation, requiring no changes to `pyproject.toml` or lock files. Adopting it will reduce CI wall
time, lower costs, and improve developer iteration speed in devcontainer environments.

## Summary

Replace `python -m pip install` with `uv pip install` in CI workflows and development setup to significantly reduce dependency resolution and install time.

## Clarifications

### Session 2026-06-03

- Q: Should special pip flags like `--force-reinstall --no-deps` (used for `github-copilot-sdk`) and `--no-deps`
  (used for the local package in `speckit-phase-progression.yml`) be preserved when switching to
  `uv pip install`, since `uv` supports these flags? → A: Yes. `uv pip install` supports `--force-reinstall`,
  `--no-deps`, and `--upgrade` flags. All existing pip flags MUST be preserved in the `uv` equivalents (e.g.,
  `uv pip install --force-reinstall --no-deps "github-copilot-sdk>=0.1.0,<1.0.0"`). The
  `python -m pip install --upgrade pip` step can be removed entirely since `uv` does not depend on pip's version.
- Q: Should `copilot-setup-steps.yml` use the `astral-sh/setup-uv@v4` action or bootstrap `uv` via pip? → A: There
  are **two distinct files** that must be treated differently. `.github/copilot-setup-steps.yml` is the Copilot cloud
  agent setup-steps file; it only supports `run:` commands (no `uses:` steps), so `uv` MUST be bootstrapped there via
  a **non-fatal** `pip install "uv>=0.7,<1.0"`
  attempt (or by folding bootstrap into the guarded install block) before calling `uv pip install`. `.github/workflows/copilot-setup-steps.yml` is a standard GitHub Actions workflow file that supports
  `uses:` steps, so it SHOULD use `astral-sh/setup-uv@v4`. The fallback guard pattern should still be included in both files for resilience.
- Q: Should the `pip install --upgrade pip` step that precedes installs in `ai-pr-loop.yml` and
  `speckit-phase-progression.yml` be retained when `uv` is the primary installer? → A: No. When `uv` is available,
  the `pip install --upgrade pip` step is unnecessary since `uv` has its own resolver. Remove the `pip --upgrade`
  step from the `uv` branch of the fallback guard. The fallback `pip` branch should still upgrade pip for
  correctness.
- Q: For the Azure DevOps pipeline (`pipelines/ai-review-stage.yaml`), which does not support the `astral-sh/setup-uv` GitHub Action, how should `uv` be provisioned? → A: In Azure DevOps pipelines,
  bootstrap `uv` via `pip install "uv>=0.7,<1.0"` (same pattern as devcontainer) before running `uv pip install`. The fallback guard pattern still applies so that if `pip install "uv>=0.7,<1.0"`
  fails for any reason, the workflow falls back to plain pip.
- Q: Should the `uv` version be pinned in CI (via `astral-sh/setup-uv@v4` `with: version:` parameter) to ensure reproducible builds, or should it always use the latest? → A: Pin to a bounded version
  constraint using `with: version: ">=0.7,<1.0"` in the `setup-uv` action (and the equivalent `pip install "uv>=0.7,<1.0"` where pip bootstrap is required). This intentionally trades strict
  reproducibility for bounded upgrades (patch/minor updates within the 0.x line) while preventing unexpected major upgrades. If strict reproducibility is required, use an exact `uv` version pin
  instead. Document the pinning rationale in a comment within the workflow file.

## Context

There is currently no usage of `uv` anywhere in the codebase. `uv` is a drop-in pip replacement written in Rust that provides 10-100x faster dependency resolution. Given that our CI workflows install
`agentic-devtools` with its full dependency tree (langgraph, azure SDKs, requests, etc.), adopting `uv` could meaningfully reduce workflow run time.

## Research

[Deep research session: no-deps and SDK install patterns](https://github.com/ayaiayorg/agentic-devtools/tasks/08202d84-f5a8-49c7-992b-1a758a6a2a89) (confirmed no existing `uv` usage in codebase)

## Implementation Steps

### 1. Add `uv` installation step to GitHub Actions workflows

Use the official GitHub Action with a minimum version pin:

```yaml
- name: Install uv
  uses: astral-sh/setup-uv@v4
  with:
    version: ">=0.7,<1.0"  # Pin to 0.x series for baseline feature support without major-version surprises
```

### 2. Add `uv` installation step to Azure DevOps pipelines

Bootstrap `uv` via pip in Azure DevOps pipelines (which cannot use GitHub Actions):

```yaml
- bash: |
    python -m pip install "uv>=0.7,<1.0"
  displayName: 'Install uv'
  continueOnError: true
```

### 3. Replace pip install commands in GitHub Actions workflows

**Files to update:**
`.github/workflows/ai-pr-loop.yml` (lines 62-66) — remove `pip install --upgrade pip`, replace remaining `python -m pip install` with `uv pip install` (preserving `--force-reinstall --no-deps` flags)
`.github/workflows/speckit-phase-progression.yml` (lines 483-487) — same replacement, preserving `--no-deps` flag on local package install
`.github/workflows/copilot-setup-steps.yml` (lines 24-25) — add `setup-uv` step, replace `pip install -e ".[dev]"` with `uv pip install -e ".[dev]"`
`.github/copilot-setup-steps.yml` (line 2) — bootstrap `uv` via a non-fatal
`pip install "uv>=0.7,<1.0"` attempt (this file only supports `run:` commands, not `uses:` steps), then replace
`pip install` with `uv pip install`

**Recommended install-step pattern:**

```yaml
- name: Install agentic-devtools
  shell: bash
  run: |
    if command -v uv >/dev/null 2>&1; then
      uv pip install agentic-devtools
    else
      python -m pip install --upgrade pip
      python -m pip install agentic-devtools
    fi
```

Use the same guard pattern for all install commands, preserving any existing flags (e.g., `--force-reinstall --no-deps`, `--no-deps`, `-e '.[dev]'`).

### 4. Replace pip install commands in Azure DevOps pipelines

**File:** `pipelines/ai-review-stage.yaml` (lines 64, 86)

**Recommended pattern:**

```yaml
- bash: |
    if command -v uv >/dev/null 2>&1; then
      uv pip install agentic-devtools
    else
      python -m pip install --upgrade pip
      python -m pip install agentic-devtools
    fi
  displayName: 'Install agentic-devtools'
```

### 5. Update devcontainer setup

**File:** `.devcontainer/devcontainer.json` (line 39)

Change:

```json
"postCreateCommand": "pip install -e '.[dev]' && git config core.hooksPath .githooks"
```

To:

```json
"postCreateCommand": "pip install 'uv>=0.7,<1.0' && uv pip install -e '.[dev]' && git config core.hooksPath .githooks"
```

This bootstraps `uv` via the system pip (which is always available in the devcontainer base image) with the same
bounded version constraint used in CI, then uses it for the actual environment installation, keeping install times
fast for local development as well.

### 6. Update documentation

Update `.devcontainer/README.md`, `.github/copilot-instructions.md`, and `docs/04-solution-strategy.md` to reference `uv` as the recommended installer and document the fallback pattern.

## User Scenarios & Testing

### User Story 1 - Happy Path: uv present in CI (Priority: P1)

As a CI pipeline, I expect all install steps to use `uv pip install` when the `astral-sh/setup-uv` action has run
successfully, so that dependency install time is meaningfully shorter than with plain pip.

**Related Functional Requirements**: FR-001, FR-002, FR-006

**Acceptance Scenarios**:

1. **Given** the `astral-sh/setup-uv@v4` action has run successfully, **When** the workflow reaches the install step,
   **Then** `uv pip install agentic-devtools` completes without error and the installed package is importable.

2. **Given** a representative CI workflow run before and after this change, **When** install time is measured,
   **Then** the `uv`-based run is faster than the pip baseline (improvement should be documented in the PR
   description).

3. **Given** a workflow that uses `--force-reinstall --no-deps` or `--no-deps` flags, **When** the install step runs with `uv`, **Then** those flags are honored and the install behaves identically to
   the pip equivalent.

### User Story 2 - Graceful Fallback: uv unavailable (Priority: P1)

As a developer running a workflow in an environment where `uv` is not installed, I expect the install step to fall
back to `python -m pip install` so that the workflow still completes successfully.

**Related Functional Requirements**: FR-003

**Acceptance Scenarios**:

1. **Given** `uv` is not present on the PATH, **When** the fallback shell guard runs, **Then** `python -m pip install`
   is executed instead and the workflow succeeds.

2. **Given** the fallback path is taken, **When** the job finishes, **Then** no error or unhandled exception is
   surfaced to the user.

3. **Given** the fallback path is taken, **When** `pip install --upgrade pip` runs in the fallback branch, **Then** pip is upgraded before installing packages to maintain existing behavior.

### User Story 3 - Devcontainer: fast local setup (Priority: P2)

As a developer opening the repository in a devcontainer, I expect the `postCreateCommand` to use `uv` so that local
environment setup is as fast as CI.

**Related Functional Requirements**: FR-004

**Acceptance Scenarios**:

1. **Given** a fresh devcontainer build, **When** `postCreateCommand` runs, **Then** `pip install "uv>=0.7,<1.0"` bootstraps `uv`
   and `uv pip install -e '.[dev]'` installs the full dev environment without error.

2. **Given** the devcontainer is fully set up, **When** `agdt-test` is run and `agdt-task-wait` confirms completion,
   **Then** all tests pass, confirming the `uv`-installed environment is functionally identical to a pip-installed
   one.

### User Story 4 - Azure DevOps Pipeline: uv bootstrapped via pip (Priority: P1)

As an Azure DevOps pipeline maintainer, I expect `uv` to be bootstrapped via `pip install "uv>=0.7,<1.0"` and then
used for subsequent installs, with a fallback to plain pip if bootstrapping fails, so that installs stay fast
without sacrificing pipeline reliability.

**Related Functional Requirements**: FR-001, FR-002, FR-003

**Acceptance Scenarios**:

1. **Given** the Azure DevOps pipeline runs `pip install "uv>=0.7,<1.0"` successfully, **When** the install step
   executes, **Then** `uv pip install agentic-devtools` is used and completes without error.

2. **Given** `pip install "uv>=0.7,<1.0"` fails (e.g., network issue or restricted environment), **When** the fallback
   guard runs, **Then** `python -m pip install agentic-devtools` is executed and the pipeline succeeds.

### User Story 5 - Documentation reflects uv-first installs (Priority: P3)

As a repository maintainer, I expect setup and strategy documentation to describe `uv` as the recommended installer so
contributors follow the same install approach used in CI and automation.

**Related Functional Requirements**: FR-005

**Acceptance Scenarios**:

1. **Given** a contributor reads `.devcontainer/README.md`, `.github/copilot-instructions.md`, or
   `docs/04-solution-strategy.md`, **When** they review installation guidance, **Then** `uv` is described as the
   recommended installer with bootstrap/fallback context where applicable.

## Requirements

### Functional Requirements

- **FR-001**: All targeted install steps in `.github/workflows/ai-pr-loop.yml`,
  `.github/workflows/speckit-phase-progression.yml`, `.github/workflows/copilot-setup-steps.yml`,
  `.github/copilot-setup-steps.yml`, and `pipelines/ai-review-stage.yaml` MUST use `uv pip install` as the primary
  path, while explicitly allowing a guarded fallback to `python -m pip install` when `uv` is unavailable.

- **FR-002**: Each GitHub Actions workflow that calls `uv pip install` MUST include a preceding step that runs
  `astral-sh/setup-uv@v4` with `version: ">=0.7,<1.0"` so that `uv` is available on the PATH before the install step executes. Azure DevOps pipelines and the Copilot cloud agent setup-steps file
  (`.github/copilot-setup-steps.yml`) MUST bootstrap `uv` via `pip install "uv>=0.7,<1.0"` in a preceding
  step, and that bootstrap MUST be non-fatal (or folded into the guarded install block) so the
  `uv`/`pip` fallback path remains reachable (those environments do not support `uses:` steps).

- **FR-003**: A pip fallback pattern MUST be available for environments where `uv` cannot be installed (e.g.,
  restricted runners), using a shell guard that detects `uv` presence and falls back to `python -m pip install` (with `pip --upgrade` in the fallback branch only).

- **FR-004**: The devcontainer `postCreateCommand` in `.devcontainer/devcontainer.json` MUST bootstrap `uv` via
  `pip install "uv>=0.7,<1.0"` and then use `uv pip install -e '.[dev]'` for the full dev environment installation.

- **FR-005**: Documentation in `.devcontainer/README.md`, `.github/copilot-instructions.md`, and
  `docs/04-solution-strategy.md` MUST be updated to reference `uv` as the recommended installer.

- **FR-006**: All existing pip flags (`--force-reinstall`, `--no-deps`, `-e`) MUST be preserved in the corresponding `uv pip install` commands. The `python -m pip install --upgrade pip` step MUST be
  removed from the `uv` code path (retained only in the fallback branch).

### Non-Functional Requirements

- **NFR-001**: Dependency installation time in CI MUST be measured and documented in the implementing PR description
  with a representative before/after wall-clock comparison; adopting `uv` is expected to improve install time, but no
  fixed percentage threshold is required for acceptance.

- **NFR-002**: The resulting installed environment (packages, versions, entry points) MUST be functionally identical
  to that produced by the existing `pip install` command, verified by passing the full test suite without changes to
  `pyproject.toml` or lock files.

## Success Criteria

- **SC-001**: `.github/workflows/ai-pr-loop.yml`, `.github/workflows/speckit-phase-progression.yml`, and
  `.github/workflows/copilot-setup-steps.yml` contain a `setup-uv` step; `.github/copilot-setup-steps.yml` and
  `pipelines/ai-review-stage.yaml` bootstrap `uv` via `pip install "uv>=0.7,<1.0"` (non-fatal for the Copilot cloud
  setup-steps context); and all targeted files use `uv pip install` as the primary install path with a guarded
  `python -m pip install` fallback.

- **SC-002**: The devcontainer `postCreateCommand` bootstraps `uv` and uses `uv pip install -e '.[dev]'`; a fresh
  devcontainer build completes without errors and the full test suite passes inside it.

- **SC-003**: A pip fallback guard is present so that workflows succeed even when `uv` is unavailable on the runner.

- **SC-004**: CI passes on the implementing PR and measured install time shows improvement over the pip baseline.

- **SC-005**: All existing pip flags (`--force-reinstall`, `--no-deps`) are preserved in the `uv` equivalents and behave identically.

---
*Generated by Copilot SDK (claude-opus-4.6)*
