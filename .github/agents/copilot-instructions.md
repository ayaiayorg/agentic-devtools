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

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python >= 3.8: Follow standard conventions

## Recent Changes
- 001-add-workflow-step-agents: Added Markdown (YAML frontmatter) for agents/prompts; Python 3.11 for optional coverage script + VS Code Copilot Chat (agent `.agent.md` and prompt `.prompt.md` conventions)
- 001-separate-docs: Added Markdown (repository documentation) + None

- 001-pypi-wheel-release: Added Python >= 3.8 + requests, Jinja2 (bestehend), neu: build, twine (für Release-Flows)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
