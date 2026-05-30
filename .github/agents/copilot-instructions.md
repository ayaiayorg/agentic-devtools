# agentic-devtools Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-02-03

## Active Technologies

- Markdown (repository documentation) + None (001-separate-docs)
- Markdown (YAML frontmatter) for agents/prompts; Python 3.11 for optional coverage script + VS Code Copilot Chat (agent `.agent.md` and prompt `.prompt.md` conventions) (001-add-workflow-step-agents)
- N/A — all artifacts are static Markdown files committed to the repository (001-add-workflow-step-agents)

- Python >= 3.8 + requests, Jinja2 (bestehend), neu: build, twine (für Release-Flows) (001-pypi-wheel-release)

## Project Structure

```text
src/
tests/
```

## Commands

```bash
cd src
pytest
ruff check .
```

## Code Style

Python >= 3.8: Follow standard conventions

## Recent Changes

- 001-add-workflow-step-agents: Added Markdown (YAML frontmatter) for agents/prompts; Python 3.11 for optional coverage script + VS Code Copilot Chat (agent `.agent.md` and prompt `.prompt.md` conventions)
- 001-separate-docs: Added Markdown (repository documentation) + None

- 001-pypi-wheel-release: Added Python >= 3.8 + requests, Jinja2 (bestehend), neu: build, twine (für Release-Flows)

<!-- MANUAL ADDITIONS START -->

## Pre-Push Hooks

When git hooks are enabled (`core.hooksPath=.githooks`), pre-push hooks enforce
the following checks before each push:

- `ruff format` — code formatting (not black)
- `ruff check` — linting and import sorting
- Per-file 100% test coverage
- `mypy` — static type checking
- Test structure validation

Markdown style is validated in CI via markdownlint on changed `.md` files.

Agents working on this repo do **not** need to manually run `ruff` or `mypy` before
pushing when hooks are enabled — the pre-push hook handles it automatically.
If push is rejected, fix the reported issues, run `agdt-git-save-work`, and retry.

## CI Pipeline (4-Tier Gates)

The CI pipeline uses the following gate names:

1. `Targeted Checks ✅` — ruff/mypy/test-structure + per-file coverage on changed files (plus markdownlint for changed `.md`)
2. `Smart Module Tests ✅` — targeted test execution for affected modules
3. `Workflow Tests ✅` — workflow integration tests for workflow-related changes
4. `Copilot Review ✅` — automated AI code review

All four gates must pass for a PR to be mergeable.

## Formatting

- Use `ruff format .` as the formatter (not black)
- Use `ruff check .` for linting (not flake8 or isort separately)

<!-- MANUAL ADDITIONS END -->
