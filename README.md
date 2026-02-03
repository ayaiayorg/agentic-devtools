# agentic-devtools

AI assistant helper commands for the Dragonfly platform. This package provides simple CLI commands that can be easily auto-approved by VS Code AI assistants.

## Spec-Driven Development (SDD) Support

This project follows [Spec-Driven Development](https://github.com/github/spec-kit) methodology. SDD enables structured feature development through executable specifications.

### Quick Start with SDD

The `.specify/` directory contains all SDD templates and tools:

```
.specify/
├── memory/
│   └── constitution.md      # Project principles and governance
├── templates/
│   ├── spec-template.md     # Feature specification template
│   ├── plan-template.md     # Implementation plan template
│   ├── tasks-template.md    # Task breakdown template
│   ├── checklist-template.md
│   └── commands/            # SDD workflow command templates
└── scripts/                 # Helper scripts (bash & PowerShell)
```

### SDD Workflow

1. **Constitution** - Define project principles (see `.specify/memory/constitution.md`)
2. **Specify** - Create feature spec in `specs/NNN-feature-name/spec.md`
3. **Plan** - Develop technical implementation plan
4. **Tasks** - Break down into actionable tasks
5. **Implement** - Execute tasks following the plan

### Creating a New Feature

```bash
# Create feature branch and spec directory
.specify/scripts/bash/create-new-feature.sh "feature-name"

# This creates:
# - Branch: NNN-feature-name
# - Directory: specs/NNN-feature-name/
# - Initial spec.md from template
```

### SDD Command Templates

AI assistants can use these command templates (in `.specify/templates/commands/`):

- `/speckit.constitution` - Update project principles
- `/speckit.specify` - Create feature specifications
- `/speckit.plan` - Develop implementation plans
- `/speckit.tasks` - Generate task lists
- `/speckit.implement` - Execute implementation
- `/speckit.analyze` - Validate cross-artifact consistency
- `/speckit.checklist` - Generate quality checklists

See individual command files for detailed execution workflows.

## Development Container

This repository includes a devcontainer configuration for Python development. To get started quickly:

- **VS Code**: Install the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers), then click "Reopen in Container"
- **GitHub Codespaces**: Create a new Codespace - all dependencies will be set up automatically

See [.devcontainer/README.md](.devcontainer/README.md) for more details.

## Installation

### Option 1: Using pipx (Recommended)

[pipx](https://pipx.pypa.io/) installs CLI tools in isolated environments with commands available globally. This is the cleanest approach.

```bash
# Install pipx if you don't have it
pip install pipx
pipx ensurepath

# ⚠️ IMPORTANT: Restart your terminal for PATH changes to take effect
# Or refresh PATH in current PowerShell session:
$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "User") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "Machine")

# Install agentic-devtools
cd agentic_devtools
pipx install .

# For development (editable install)
pipx install -e .
```

### Option 2: Global pip install

Install directly into your system Python. May require administrator privileges on Windows.

```bash
cd agentic_devtools

# Global install (may need admin/sudo)
pip install .

# For development (editable)
pip install -e .

# With dev dependencies
pip install -e ".[dev]"
```

> **Note:** Avoid `pip install --user` as it places scripts in a directory that may not be on your PATH (`%APPDATA%\Python\PythonXXX\Scripts` on Windows).

### Verify Installation

After installation, verify the commands are available:

```bash
agdt-set --help
agdt-show
```

If commands are not found after installation:

- **pipx:** Run `pipx ensurepath` and restart your terminal
- **pip global:** Ensure `C:\PythonXXX\Scripts` (or equivalent) is on your PATH

## Design Principles

1. **Auto-approvable commands**: Commands are designed to be auto-approved by VS Code
2. **JSON state file**: Single `agdt-state.json` file stores all parameters
3. **Generic set/get pattern**: One `agdt-set` command works for all keys (approve once, use for everything)
4. **Native special character support**: Python CLI handles `()[]{}` and multiline content directly!
5. **Test-driven development**: Tests first with strict coverage expectations
6. **UX consistency**: Predictable command patterns and actionable output
7. **Performance responsiveness**: Long-running operations use background tasks

## Quick Start

```bash
# Set state values (approve agdt-set once, use for any key)
agdt-set pr_id 23046
agdt-set thread_id 139474
agdt-set content "Thanks for the feedback!

I've made the changes you suggested."

# Execute action (parameterless - approve once)
agdt-reply-to-pr-thread
```

## State Management Commands

```bash
# Set any key-value pair
agdt-set <key> <value>

# Get a value
agdt-get <key>

# Delete a key
agdt-delete <key>

# Clear all state
agdt-clear

# Show all state
agdt-show
```

### Examples

```bash
# Simple values
agdt-set pr_id 23046
agdt-set thread_id 139474
agdt-set dry_run true

# Content with special characters (works directly!)
agdt-set content "Fix: handle (optional) [array] parameters"

# Multiline content (works directly!)
agdt-set content "Thanks for the feedback!

I've addressed your concerns:
- Fixed the null check
- Added unit tests
- Updated documentation"

# View current state
agdt-show
```

## Azure DevOps Commands

### Reply to PR Thread

```bash
agdt-set pr_id 23046
agdt-set thread_id 139474
agdt-set content "Your reply message"
agdt-reply-to-pr-thread

# Optionally resolve the thread after replying
agdt-set resolve_thread true
agdt-reply-to-pr-thread
```

### Add New PR Comment

```bash
agdt-set pr_id 23046
agdt-set content "Your comment"
agdt-add-pr-comment

# For file-level comment
agdt-set path "src/example.py"
agdt-set line 42
agdt-add-pr-comment
```

### Dry Run Mode

```bash
agdt-set dry_run true
agdt-reply-to-pr-thread  # Previews without making API calls
```

## Git Commands

The package provides streamlined Git workflow commands that support the single-commit policy.

### Initial Commit & Publish

```bash
# Option A: With CLI parameter (explicit)
agdt-git-save-work --commit-message "feature([DFLY-1234](https://jira.swica.ch/browse/DFLY-1234)): add feature

- Change 1
- Change 2

[DFLY-1234](https://jira.swica.ch/browse/DFLY-1234)"

# Option B: Parameterless (uses current state)
# Current commit_message: run `agdt-get commit_message` to check
agdt-git-save-work
```

### Smart Commit (Auto-detects Amend)

The `agdt-git-save-work` command automatically detects if you're updating an existing commit:

```bash
# First commit - creates new commit and publishes branch
agdt-git-save-work --commit-message "feature(DFLY-1234): initial implementation"

# Subsequent commits on same issue - automatically amends and force pushes
agdt-git-save-work --commit-message "feature(DFLY-1234): refined implementation

- Original changes
- Additional updates"
# Auto-detects and amends!
```

**Detection logic:**

1. If branch has commits ahead of `origin/main` AND
2. Last commit message contains the current Jira issue key (from `jira.issue_key` state)
3. Then: amend existing commit and force push
4. Otherwise: create new commit and publish

### Individual Git Operations

```bash
agdt-git-stage       # Stage all changes (git add .)
agdt-git-push        # Push changes (git push)
agdt-git-force-push  # Force push with lease
agdt-git-publish     # Push with upstream tracking
```

### Git State Options

| Key              | Purpose                                          |
| ---------------- | ------------------------------------------------ |
| `commit_message` | The commit message (multiline supported)         |
| `dry_run`        | If true, preview commands without executing      |
| `skip_stage`     | If true, skip staging step                       |
| `skip_push`      | If true, skip push step (for agdt-git-save-work) |

## Workflow Commands

The package provides workflow commands for managing structured work processes.

### Work on Jira Issue Workflow

```bash
# Start work on a Jira issue
agdt-set jira.issue_key "DFLY-1234"
agdt-initiate-work-on-jira-issue-workflow
```

**Workflow Steps:**

1. **setup** - Create worktree and branch (if pre-flight fails)
2. **retrieve** - Auto-fetches Jira issue details
3. **planning** - Analyze issue and post plan comment to Jira
4. **checklist-creation** - Create implementation checklist from plan
5. **implementation** - Code changes, tests, documentation
6. **implementation-review** - Review completed checklist items
7. **verification** - Run tests and quality gates
8. **commit** - Stage and commit changes
9. **pull-request** - Create PR
10. **completion** - Post final Jira comment

### Checklist Management

```bash
# Create implementation checklist
agdt-create-checklist "item1" "item2" "item3"

# Update checklist (mark items complete)
agdt-update-checklist --completed 1 3  # Mark items 1 and 3 as complete

# View current checklist
agdt-show-checklist

# Update during commit (auto-marks items and advances workflow)
agdt-git-save-work --completed 1 2  # Marks items complete before committing
```

### Workflow Navigation

```bash
# View current workflow state
agdt-get-workflow

# Advance to next step
agdt-advance-workflow

# Clear workflow
agdt-clear-workflow
```

## PyPI Release Commands

Verwende die `pypi.*` Namespace-Keys für Release-Parameter. Setze deine PyPI Tokens via Umgebungsvariablen:

- `TWINE_USERNAME=__token__`
- `TWINE_PASSWORD=<pypi-token>`

### PyPI Release starten

```bash
# Parameter setzen
agdt-set pypi.package_name agentic-devtools
agdt-set pypi.version 0.1.0
agdt-set pypi.repository pypi  # oder testpypi
agdt-set pypi.dry_run false

# Release starten (parameterlos)
agdt-release-pypi
```

### Status prüfen

```bash
agdt-task-status
agdt-task-log
agdt-task-wait
```

## Jira Commands

All Jira commands use the `jira.*` namespace for state values. Set `JIRA_COPILOT_PAT` environment variable with your Jira API token.

### Get Issue Details

```bash
agdt-set jira.issue_key "DFLY-1234"
agdt-get-jira-issue
```

### Add Comment to Issue

Commands with optional CLI parameters support two usage patterns:

```bash
# Option A: With CLI parameters (explicit)
agdt-add-jira-comment --jira-comment "Your comment text"

# Option B: Parameterless (uses current state)
# Current jira.issue_key: run `agdt-get jira.issue_key` to check
# Current jira.comment: run `agdt-get jira.comment` to check
agdt-add-jira-comment
```

### Create Epic

```bash
agdt-set jira.project_key "DFLY"
agdt-set jira.summary "Epic Title"
agdt-set jira.epic_name "EPIC-KEY"
agdt-set jira.role "developer"
agdt-set jira.desired_outcome "implement feature"
agdt-set jira.benefit "improved UX"
agdt-create-epic

# Optional: Add acceptance criteria
agdt-set jira.acceptance_criteria "- Criterion 1
- Criterion 2"
agdt-create-epic
```

### Create Issue (Task/Bug/Story)

```bash
agdt-set jira.project_key "DFLY"
agdt-set jira.summary "Issue Title"
agdt-set jira.description "Issue description"
agdt-create-issue

# Or use user story format
agdt-set jira.role "developer"
agdt-set jira.desired_outcome "complete task"
agdt-set jira.benefit "value delivered"
agdt-create-issue
```

### Create Subtask

```bash
agdt-set jira.parent_key "DFLY-1234"
agdt-set jira.summary "Subtask Title"
agdt-set jira.description "Subtask description"
agdt-create-subtask
```

### Dry Run Mode for Jira

```bash
agdt-set jira.dry_run true
agdt-create-issue  # Previews payload without API call
```

## Environment Variables

| Variable                    | Purpose                                             |
| --------------------------- | --------------------------------------------------- |
| `AZURE_DEV_OPS_COPILOT_PAT` | Azure DevOps PAT for API calls                      |
| `JIRA_COPILOT_PAT`          | Jira API token for authentication                   |
| `JIRA_BASE_URL`             | Override default Jira URL (default: jira.swica.ch)  |
| `JIRA_SSL_VERIFY`           | Set to `0` to disable SSL verification              |
| `JIRA_CA_BUNDLE`            | Path to custom CA bundle PEM file for Jira SSL      |
| `REQUESTS_CA_BUNDLE`        | Standard requests library CA bundle path (fallback) |
| `AGDT_STATE_FILE`           | Override default state file path                    |

## State File Location

By default, state is stored in `scripts/temp/agdt-state.json` (relative to the repo root).

## Why This Design?

### Auto-Approval Friendly

VS Code's auto-approval matches exact command strings. By using:

- Generic `agdt-set key value` - approve once, use for any key
- Parameterless action commands like `agdt-reply-to-pr-thread`

...you only need to approve a few commands once, then they work for all future operations.

### No Replacement Tokens Needed

Unlike PowerShell, Python's CLI parsing handles special characters natively:

```bash
# This just works!
agdt-set content "Code with (parentheses) and [brackets]"
```

### No Multi-line Builder Needed

Python preserves multiline strings from the shell:

```bash
agdt-set content "Line 1
Line 2
Line 3"
```

## Development

### Testing Commands

The package provides test commands that can be auto-approved:

```bash
# Run full test suite with coverage
agdt-test

# Run tests quickly (no coverage)
agdt-test-quick

# Run specific test file, class, or method
agdt-test-pattern tests/test_jira_helpers.py
agdt-test-pattern tests/test_jira_helpers.py::TestEnsureJiraPem
agdt-test-pattern tests/test_jira_helpers.py::TestEnsureJiraPem::test_returns_existing_pem_path

# Run tests using state (alternative)
agdt-set test_pattern test_jira_helpers.py
agdt-test-file
```

### Manual pytest

Run tests:

```bash
pytest
```

Run with coverage:

```bash
pytest --cov=agentic_devtools
```
