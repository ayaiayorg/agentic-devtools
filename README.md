# agentic-devtools

AI assistant helper commands for the Dragonfly platform. This package provides simple CLI commands that can be easily auto-approved by VS Code AI assistants.

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
dfly-set --help
dfly-show
```

If commands are not found after installation:

- **pipx:** Run `pipx ensurepath` and restart your terminal
- **pip global:** Ensure `C:\PythonXXX\Scripts` (or equivalent) is on your PATH

## Design Principles

1. **Auto-approvable commands**: Commands are designed to be auto-approved by VS Code
2. **JSON state file**: Single `dfly-state.json` file stores all parameters
3. **Generic set/get pattern**: One `dfly-set` command works for all keys (approve once, use for everything)
4. **Native special character support**: Python CLI handles `()[]{}` and multiline content directly!

## Quick Start

```bash
# Set state values (approve dfly-set once, use for any key)
dfly-set pr_id 23046
dfly-set thread_id 139474
dfly-set content "Thanks for the feedback!

I've made the changes you suggested."

# Execute action (parameterless - approve once)
dfly-reply-to-pr-thread
```

## State Management Commands

```bash
# Set any key-value pair
dfly-set <key> <value>

# Get a value
dfly-get <key>

# Delete a key
dfly-delete <key>

# Clear all state
dfly-clear

# Show all state
dfly-show
```

### Examples

```bash
# Simple values
dfly-set pr_id 23046
dfly-set thread_id 139474
dfly-set dry_run true

# Content with special characters (works directly!)
dfly-set content "Fix: handle (optional) [array] parameters"

# Multiline content (works directly!)
dfly-set content "Thanks for the feedback!

I've addressed your concerns:
- Fixed the null check
- Added unit tests
- Updated documentation"

# View current state
dfly-show
```

## Azure DevOps Commands

### Reply to PR Thread

```bash
dfly-set pr_id 23046
dfly-set thread_id 139474
dfly-set content "Your reply message"
dfly-reply-to-pr-thread

# Optionally resolve the thread after replying
dfly-set resolve_thread true
dfly-reply-to-pr-thread
```

### Add New PR Comment

```bash
dfly-set pr_id 23046
dfly-set content "Your comment"
dfly-add-pr-comment

# For file-level comment
dfly-set path "src/example.py"
dfly-set line 42
dfly-add-pr-comment
```

### Dry Run Mode

```bash
dfly-set dry_run true
dfly-reply-to-pr-thread  # Previews without making API calls
```

## Git Commands

The package provides streamlined Git workflow commands that support the single-commit policy.

### Initial Commit & Publish

```bash
# Option A: With CLI parameter (explicit)
dfly-git-save-work --commit-message "feature([DFLY-1234](https://jira.swica.ch/browse/DFLY-1234)): add feature

- Change 1
- Change 2

[DFLY-1234](https://jira.swica.ch/browse/DFLY-1234)"

# Option B: Parameterless (uses current state)
# Current commit_message: run `dfly-get commit_message` to check
dfly-git-save-work
```

### Smart Commit (Auto-detects Amend)

The `dfly-git-save-work` command automatically detects if you're updating an existing commit:

```bash
# First commit - creates new commit and publishes branch
dfly-git-save-work --commit-message "feature(DFLY-1234): initial implementation"

# Subsequent commits on same issue - automatically amends and force pushes
dfly-git-save-work --commit-message "feature(DFLY-1234): refined implementation

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
dfly-git-stage       # Stage all changes (git add .)
dfly-git-push        # Push changes (git push)
dfly-git-force-push  # Force push with lease
dfly-git-publish     # Push with upstream tracking
```

### Git State Options

| Key              | Purpose                                          |
| ---------------- | ------------------------------------------------ |
| `commit_message` | The commit message (multiline supported)         |
| `dry_run`        | If true, preview commands without executing      |
| `skip_stage`     | If true, skip staging step                       |
| `skip_push`      | If true, skip push step (for dfly-git-save-work) |

## Workflow Commands

The package provides workflow commands for managing structured work processes.

### Work on Jira Issue Workflow

```bash
# Start work on a Jira issue
dfly-set jira.issue_key "DFLY-1234"
dfly-initiate-work-on-jira-issue-workflow
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
dfly-create-checklist "item1" "item2" "item3"

# Update checklist (mark items complete)
dfly-update-checklist --completed 1 3  # Mark items 1 and 3 as complete

# View current checklist
dfly-show-checklist

# Update during commit (auto-marks items and advances workflow)
dfly-git-save-work --completed 1 2  # Marks items complete before committing
```

### Workflow Navigation

```bash
# View current workflow state
dfly-get-workflow

# Advance to next step
dfly-advance-workflow

# Clear workflow
dfly-clear-workflow
```

## Jira Commands

All Jira commands use the `jira.*` namespace for state values. Set `JIRA_COPILOT_PAT` environment variable with your Jira API token.

### Get Issue Details

```bash
dfly-set jira.issue_key "DFLY-1234"
dfly-get-jira-issue
```

### Add Comment to Issue

Commands with optional CLI parameters support two usage patterns:

```bash
# Option A: With CLI parameters (explicit)
dfly-add-jira-comment --jira-comment "Your comment text"

# Option B: Parameterless (uses current state)
# Current jira.issue_key: run `dfly-get jira.issue_key` to check
# Current jira.comment: run `dfly-get jira.comment` to check
dfly-add-jira-comment
```

### Create Epic

```bash
dfly-set jira.project_key "DFLY"
dfly-set jira.summary "Epic Title"
dfly-set jira.epic_name "EPIC-KEY"
dfly-set jira.role "developer"
dfly-set jira.desired_outcome "implement feature"
dfly-set jira.benefit "improved UX"
dfly-create-epic

# Optional: Add acceptance criteria
dfly-set jira.acceptance_criteria "- Criterion 1
- Criterion 2"
dfly-create-epic
```

### Create Issue (Task/Bug/Story)

```bash
dfly-set jira.project_key "DFLY"
dfly-set jira.summary "Issue Title"
dfly-set jira.description "Issue description"
dfly-create-issue

# Or use user story format
dfly-set jira.role "developer"
dfly-set jira.desired_outcome "complete task"
dfly-set jira.benefit "value delivered"
dfly-create-issue
```

### Create Subtask

```bash
dfly-set jira.parent_key "DFLY-1234"
dfly-set jira.summary "Subtask Title"
dfly-set jira.description "Subtask description"
dfly-create-subtask
```

### Dry Run Mode for Jira

```bash
dfly-set jira.dry_run true
dfly-create-issue  # Previews payload without API call
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
| `DFLY_STATE_FILE`           | Override default state file path                    |

## State File Location

By default, state is stored in `scripts/temp/dfly-state.json` (relative to the repo root).

## Why This Design?

### Auto-Approval Friendly

VS Code's auto-approval matches exact command strings. By using:

- Generic `dfly-set key value` - approve once, use for any key
- Parameterless action commands like `dfly-reply-to-pr-thread`

...you only need to approve a few commands once, then they work for all future operations.

### No Replacement Tokens Needed

Unlike PowerShell, Python's CLI parsing handles special characters natively:

```bash
# This just works!
dfly-set content "Code with (parentheses) and [brackets]"
```

### No Multi-line Builder Needed

Python preserves multiline strings from the shell:

```bash
dfly-set content "Line 1
Line 2
Line 3"
```

## Development

### Testing Commands

The package provides test commands that can be auto-approved:

```bash
# Run full test suite with coverage
dfly-test

# Run tests quickly (no coverage)
dfly-test-quick

# Run specific test file, class, or method
dfly-test-pattern tests/test_jira_helpers.py
dfly-test-pattern tests/test_jira_helpers.py::TestEnsureJiraPem
dfly-test-pattern tests/test_jira_helpers.py::TestEnsureJiraPem::test_returns_existing_pem_path

# Run tests using state (alternative)
dfly-set test_pattern test_jira_helpers.py
dfly-test-file
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
