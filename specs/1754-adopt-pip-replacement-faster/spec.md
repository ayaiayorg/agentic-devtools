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

## Context

There is currently no usage of `uv` anywhere in the codebase. `uv` is a drop-in pip replacement written in Rust that provides 10-100x faster dependency resolution. Given that our CI workflows install
`agentic-devtools` with its full dependency tree (langgraph, azure SDKs, requests, etc.), adopting `uv` could meaningfully reduce workflow run time.

## Research

[Deep research session: no-deps and SDK install patterns](https://github.com/ayaiayorg/agentic-devtools/tasks/08202d84-f5a8-49c7-992b-1a758a6a2a89) (confirmed no existing `uv` usage in codebase)

## Implementation Steps

### 1. Add `uv` installation step to workflows

Use the official GitHub Action:

```yaml
- name: Install uv
  uses: astral-sh/setup-uv@v4
```

### 2. Replace pip install commands in workflows

**Files to update:**
`.github/workflows/ai-pr-loop.yml` (line 62-66) — replace `python -m pip install` with `uv pip install`
`.github/workflows/speckit-phase-progression.yml` (lines 483-487) — same replacement
`.github/copilot-setup-steps.yml` (line 2) — replace `pip install 'agentic-devtools[dev]'` with `uv pip install 'agentic-devtools[dev]'`
`pipelines/ai-review-stage.yaml` (lines 64, 86) — replace `python -m pip install agentic-devtools` with `uv pip install agentic-devtools`

**Recommended install-step pattern:**

```yaml
- name: Install agentic-devtools
  shell: bash
  run: |
    if command -v uv >/dev/null 2>&1; then
      uv pip install agentic-devtools
    else
      python -m pip install agentic-devtools
    fi
```

Use the same guard pattern for editable/dev installs (for example, `uv pip install -e '.[dev]'` with a
`python -m pip install -e '.[dev]'` fallback) so all workflows handle restricted runners consistently.

### 3. Update devcontainer setup

**File:** `.devcontainer/devcontainer.json` (line 39)

Change:

```json
"postCreateCommand": "pip install -e '.[dev]' && git config core.hooksPath .githooks"
```

To:

```json
"postCreateCommand": "pip install uv && uv pip install -e '.[dev]' && git config core.hooksPath .githooks"
```

This bootstraps `uv` via the system pip (which is always available in the devcontainer base image) and then uses it
for the actual environment installation, keeping install times fast for local development as well.

## User Scenarios & Testing

### User Story 1 - Happy Path: uv present in CI (Priority: P1)

As a CI pipeline, I expect all install steps to use `uv pip install` when the `astral-sh/setup-uv` action has run
successfully, so that dependency install time is meaningfully shorter than with plain pip.

**Acceptance Scenarios**:

1. **Given** the `astral-sh/setup-uv@v4` action has run successfully, **When** the workflow reaches the install step,
   **Then** `uv pip install agentic-devtools` completes without error and the installed package is importable.

2. **Given** a representative CI workflow run before and after this change, **When** install time is measured,
   **Then** the `uv`-based run is faster than the pip baseline (improvement should be documented in the PR
   description).

### User Story 2 - Graceful Fallback: uv unavailable (Priority: P1)

As a developer running a workflow in an environment where `uv` is not installed, I expect the install step to fall
back to `python -m pip install` so that the workflow still completes successfully.

**Acceptance Scenarios**:

1. **Given** `uv` is not present on the PATH, **When** the fallback shell guard runs, **Then** `python -m pip install`
   is executed instead and the workflow succeeds.

2. **Given** the fallback path is taken, **When** the job finishes, **Then** no error or unhandled exception is
   surfaced to the user.

### User Story 3 - Devcontainer: fast local setup (Priority: P2)

As a developer opening the repository in a devcontainer, I expect the `postCreateCommand` to use `uv` so that local
environment setup is as fast as CI.

**Acceptance Scenarios**:

1. **Given** a fresh devcontainer build, **When** `postCreateCommand` runs, **Then** `pip install uv` bootstraps `uv`
   and `uv pip install -e '.[dev]'` installs the full dev environment without error.

2. **Given** the devcontainer is fully set up, **When** `agdt-test` is run and `agdt-task-wait` confirms completion,
   **Then** all tests pass, confirming the `uv`-installed environment is functionally identical to a pip-installed
   one.

## Requirements

### Functional Requirements

- **FR-001**: All CI workflow install steps (`ai-pr-loop.yml`, `speckit-phase-progression.yml`,
  `copilot-setup-steps.yml`, `pipelines/ai-review-stage.yaml`) MUST use `uv pip install` as the primary install
  path after running the `astral-sh/setup-uv@v4` action to acquire `uv`, while explicitly allowing a fallback to
  `python -m pip install` when `uv` is unavailable.

- **FR-002**: Each workflow that calls `uv pip install` MUST include a preceding step that runs
  `astral-sh/setup-uv@v4` (or equivalent) so that `uv` is available on the PATH before the install step executes.

- **FR-003**: A pip fallback pattern MUST be available for environments where `uv` cannot be installed (e.g.,
  restricted runners), using a shell guard that detects `uv` presence and falls back to `python -m pip install`.

- **FR-004**: The devcontainer `postCreateCommand` in `.devcontainer/devcontainer.json` MUST bootstrap `uv` via
  `pip install uv` and then use `uv pip install -e '.[dev]'` for the full dev environment installation.

- **FR-005**: Documentation in `.devcontainer/README.md`, `.github/copilot-instructions.md`, and
  `docs/04-solution-strategy.md` MUST be updated to reference `uv` as the recommended installer.

### Non-Functional Requirements

- **NFR-001**: Dependency installation time in CI MUST be measurably shorter after adopting `uv`; the improvement must
  be documented in the implementing PR description (before/after wall-clock comparison from a representative workflow
  run).

- **NFR-002**: The resulting installed environment (packages, versions, entry points) MUST be functionally identical
  to that produced by the existing `pip install` command, verified by passing the full test suite without changes to
  `pyproject.toml` or lock files.

## Success Criteria

- **SC-001**: All targeted workflow files (`ai-pr-loop.yml`, `speckit-phase-progression.yml`,
  `copilot-setup-steps.yml`, `pipelines/ai-review-stage.yaml`) contain a `setup-uv` step and use `uv pip install`
  as the primary install path while retaining a guarded `python -m pip install` fallback.

- **SC-002**: The devcontainer `postCreateCommand` bootstraps `uv` and uses `uv pip install -e '.[dev]'`; a fresh
  devcontainer build completes without errors and the full test suite passes inside it.

- **SC-003**: A pip fallback guard is present so that workflows succeed even when `uv` is unavailable on the runner.

- **SC-004**: CI passes on the implementing PR and measured install time shows improvement over the pip baseline.

---
*Generated by Copilot SDK (claude-opus-4.6)*
