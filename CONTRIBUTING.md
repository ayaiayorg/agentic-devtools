# Contributing to agentic-devtools

Thank you for your interest in contributing to agentic-devtools! This guide will help you get started with development, testing, and submitting changes.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- pip or pipx

### Clone the Repository

```bash
git clone https://github.com/ayaiayorg/agentic-devtools.git
cd agentic-devtools
```

### Development Environment Setup

#### Option 1: Dev Container (Recommended)

This repository includes a dev container configuration for Python development. This is the easiest way to get started:

- **VS Code**: Install the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers), then click "Reopen in Container"
- **GitHub Codespaces**: Create a new Codespace - all dependencies will be set up automatically

See [.devcontainer/README.md](.devcontainer/README.md) for more details.

#### Option 2: Local Development

Install the package in editable mode with development dependencies:

```bash
pip install -e ".[dev]"
```

This installs agentic-devtools with all development tools including pytest, black, isort, mypy, and ruff.

## Running Tests

### Test Organization Policy

New unit tests must follow the **1:1:1 policy**: one test file per symbol (function or class), in a directory
that mirrors the source structure. See [tests/README.md](tests/README.md) for the full policy,
rationale, and how to add new tests.

**Quick path convention:**

```text
tests/unit/{module_path}/{source_file_name}/test_{symbol_name}.py
```

Run the structure validator before pushing:

```bash
python scripts/validate_test_structure.py
```

### Full Test Suite

Run the complete test suite with coverage:

```bash
pytest --cov=agentic_devtools --cov-report=term-missing
```

**Note for AGDT contributors**: Use the `agdt-test` commands instead of running pytest directly:

```bash
# Run full test suite with coverage (background task)
agdt-test
agdt-task-wait

# Run tests quickly without coverage
agdt-test-quick
agdt-task-wait

# Run specific test file or pattern (synchronous)
agdt-test-pattern tests/test_jira_helpers.py
agdt-test-pattern tests/test_jira_helpers.py::TestClassName::test_method
```

### E2E Smoke Tests

End-to-end smoke tests verify the complete workflow including Azure DevOps and Jira integration. These tests are located in the `tests/` directory and typically require environment variables to be set:

- `AZURE_DEV_OPS_COPILOT_PAT` - Azure DevOps Personal Access Token
- `JIRA_COPILOT_PAT` - Jira API token
- `JIRA_BASE_URL` - Jira instance URL

Run E2E tests with:

```bash
pytest tests/test_e2e_*.py -v
```

## TDD Workflow

This project requires **Test-Driven Development (TDD)** for all implementation work.
Write tests **before** implementation code. The red-green-refactor cycle is mandatory.

### Red-Green-Refactor Cycle

1. **RED** — Write a failing test that defines the expected behaviour. Run it to confirm it fails.
2. **GREEN** — Write the minimal implementation to make the test pass. Run it to confirm it passes.
3. **REFACTOR** — Improve code structure and clarity while keeping tests green.

### TDD Example

```bash
# 1. Write the test first (no source changes yet)
# Create tests/unit/cli/git/core/test_new_function.py

# 2. Confirm the test fails (RED)
agdt-test-pattern tests/unit/cli/git/core/test_new_function.py -v
# Expected: FAILED

# 3. Write minimal implementation
# Edit agentic_devtools/cli/git/core.py

# 4. Confirm tests pass (GREEN)
agdt-test-pattern tests/unit/cli/git/core/test_new_function.py -v
# Expected: PASSED

# 5. Refactor and verify coverage (REFACTOR)
agdt-test-file --source-file agentic_devtools/cli/git/core.py
agdt-task-wait

# 6. Run the full suite when all work is complete
agdt-test
agdt-task-wait
```

### Rules

- Never write source code before a failing test exists.
- Never skip the RED step — a test that passes without any implementation is not testing anything.
- Keep each RED → GREEN cycle small: one function or behaviour at a time.
- All new code must maintain 100% test coverage (enforced by CI).

## Code Quality

We maintain high code quality standards using multiple tools. All code must pass these checks before being merged.

### Formatting

**Black**: Code formatting

```bash
black agentic_devtools tests
```

**isort**: Import sorting

```bash
isort agentic_devtools tests
```

### Type Checking

**mypy**: Static type checking

```bash
mypy agentic_devtools
```

### Linting

**ruff**: Fast Python linter

```bash
ruff check agentic_devtools tests
```

**markdownlint**: Markdown linting

```bash
markdownlint-cli2 "**/*.md"
```

### Running All Quality Checks

Run all quality checks at once:

```bash
# Format code
black agentic_devtools tests
isort agentic_devtools tests

# Check types
mypy agentic_devtools

# Lint code
ruff check agentic_devtools tests

# Lint markdown
markdownlint-cli2 "**/*.md"
```

## Spec-Driven Development

This project follows the Spec-Driven Development (SDD) methodology. Before implementing new features:

1. Create a feature specification in `specs/NNN-feature-name/spec.md`
2. Develop an implementation plan in `specs/NNN-feature-name/plan.md`
3. Break down the work into tasks in `specs/NNN-feature-name/tasks.md`
4. Implement following the plan

For complete details on the SDD workflow, see [SPEC_DRIVEN_DEVELOPMENT.md](SPEC_DRIVEN_DEVELOPMENT.md).

### SDD Helper Commands

AI assistants can use these commands:

- `/speckit.specify` - Create feature specifications
- `/speckit.plan` - Develop implementation plans
- `/speckit.tasks` - Generate task lists
- `/speckit.implement` - Execute implementation
- `/speckit.analyze` - Validate cross-artifact consistency

## Protected / Auto-Generated Files

> **⚠️ IMPORTANT — AI AGENTS AND CONTRIBUTORS: Do NOT manually edit or commit these files.**

### `agentic_devtools/_version.py`

This file is **automatically generated** by `hatch-vcs` / `setuptools-scm` from Git tags at build
time. Its header says: _"file generated by setuptools-scm — don't change, don't track in version
control"_.

- The file is listed in `.gitignore` and is **not tracked by git**.
- Do **not** create, edit, or `git add` this file during development.
- Version numbers are derived from Git tags — to bump the version, create a new Git tag
  (see [RELEASING.md](RELEASING.md)).

Because the file is untracked, `.gitignore` prevents `git add .` from ever staging it — no
additional configuration is needed for either agent or developer workflows.

## Submitting Changes

### Branch Naming

Use descriptive branch names with the following patterns:

- `feature/ISSUE-KEY/description` - For new features
- `fix/ISSUE-KEY/description` - For bug fixes
- `docs/description` - For documentation changes
- `refactor/description` - For refactoring

Example: `feature/DFLY-1234/add-webhook-support`

### Single-Commit Policy

We follow a single-commit-per-PR policy:

- Each PR should contain exactly one commit
- Commit messages should follow conventional commit format: `type(scope): description`
- When making updates to a PR, amend the existing commit and force-push

Example commit messages:

```text
feature(DFLY-1234): add webhook support for Jira events
fix(DFLY-5678): handle null values in PR thread API
docs: update CONTRIBUTING.md with new guidelines
```

### Pull Request Process

1. **Create a feature branch** following the naming convention
2. **Make your changes** following the code quality standards
3. **Write tests** to cover your changes
4. **Run all quality checks** (formatting, linting, type checking, tests)
5. **Commit your changes** with a descriptive message
6. **Push your branch** and create a pull request
7. **Address review feedback** by amending your commit
8. **Wait for CI checks** to pass before requesting final review

### Code Review

All PRs require code review before merging. Reviews check for:

- Code quality and adherence to standards
- Test coverage (aim for >90%)
- Documentation updates
- Compliance with SDD principles (if applicable)
- Security considerations

## Reporting Issues

### Bug Reports

When reporting bugs, please include:

- **Description**: Clear description of the issue
- **Steps to Reproduce**: Detailed steps to reproduce the problem
- **Expected Behavior**: What you expected to happen
- **Actual Behavior**: What actually happened
- **Environment**: Python version, OS, relevant package versions
- **Logs**: Any error messages or stack traces

### Feature Requests

For feature requests, please provide:

- **Use Case**: Why is this feature needed?
- **Proposed Solution**: How should it work?
- **Alternatives**: Have you considered other approaches?
- **Additional Context**: Any other relevant information

### Security Issues

For security vulnerabilities, please follow responsible disclosure:

1. **Do not** open a public issue
2. Email the maintainers directly with details
3. Allow time for the issue to be addressed before public disclosure

## Development Tips

### Using State Management

The package uses a JSON state file (`scripts/temp/agdt-state.json`) for parameter passing:

```bash
# Set values
agdt-set pr_id 23046
agdt-set content "Your message"

# Get values
agdt-get pr_id
```

### Background Tasks

Many commands run as background tasks. Monitor them with:

```bash
agdt-tasks              # List all tasks
agdt-task-status        # Check specific task status
agdt-task-log           # View task logs
agdt-task-wait          # Wait for task completion
```

### Debugging

Enable dry-run mode to preview operations without executing:

```bash
agdt-set dry_run true
agdt-git-save-work  # Previews commands without executing
```

## Additional Resources

- [README.md](README.md) - End-user documentation
- [SPEC_DRIVEN_DEVELOPMENT.md](SPEC_DRIVEN_DEVELOPMENT.md) - SDD workflow guide
- [RELEASING.md](RELEASING.md) - Release process documentation
- [.devcontainer/README.md](.devcontainer/README.md) - Dev container setup

## Questions?

If you have questions or need help:

- Open a discussion in the GitHub repository
- Check existing issues for similar questions
- Reach out to the maintainers

Thank you for contributing to agentic-devtools! 🎉
