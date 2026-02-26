# agentic-devtools

AI assistant helper commands for the Dragonfly platform. This package provides
simple CLI commands that can be easily auto-approved by VS Code AI assistants.

**Audience**: End users of the AGDT CLI. This README focuses on installation
and
usage.

## Installation

### Option 1: Using pipx (Recommended)

A pip-installable Python package that provides CLI commands for AI agents
to interact with Git, Azure DevOps, Jira, and other services.

```bash
# Install pipx if you don't have it
pip install pipx
pipx ensurepath

# ⚠️ IMPORTANT: Restart your terminal for PATH changes to take effect
# Or refresh PATH in current PowerShell session:
Workflow steps can be started from VS Code Copilot Chat using
`/agdt.<workflow>.<step>` commands.

# Install agentic-devtools
cd agentic_devtools
pipx install .

# For development (editable install)
pipx install -e .
```text

### Option 2: Global pip install

Install directly into your system Python. May require administrator privileges
on Windows.

```bash
cd agentic_devtools

# Global install (may need admin/sudo)
pip install .

# For development (editable)
pip install -e .

# With dev dependencies
pip install -e ".[dev]"
```text

> **Note:** Avoid `pip install --user` as it places scripts in a directory that
may not be on your PATH (`%APPDATA%\Python\PythonXXX\Scripts` on Windows).

### Verify Installation

After installation, verify the commands are available:

```bash
agdt-set --help
agdt-show
```text

If commands are not found after installation:

- **pipx:** Run `pipx ensurepath` and restart your terminal
- **pip global:** Ensure `C:\PythonXXX\Scripts` (or equivalent) is on your PATH

## Design Principles

1. **Auto-approvable commands**: Commands are designed to be auto-approved by
   VS Code
2. **JSON state file**: Single `agdt-state.json` file stores all parameters
3. **Generic set/get pattern**: One `agdt-set` command works for all keys
   (approve once, use for everything)
4. **Native special character support**: Python CLI handles `()[]{}` and
   multiline content directly!
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
```text

## Copilot Commands

Agents are available in two contexts:

**VS Code Copilot Chat** — type `/` to browse all commands:

```
/speckit.specify Add a dark mode toggle    ← SDD: create spec
/speckit.plan                              ← SDD: generate plan
/speckit.implement                         ← SDD: execute tasks
/agdt.work-on-jira-issue.initiate DFLY-1  ← Jira workflow (11 steps)
/agdt.pull-request-review.initiate        ← PR review (5 steps)
```

**Terminal Copilot CLI** — ask naturally or use shell commands:

```bash
agdt-speckit-analyze      # renders + prints the speckit.analyze prompt
agdt-speckit-specify "add dark mode"
```

📖 **Full reference**: [docs/copilot-commands.md](docs/copilot-commands.md)

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
```text

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
```text

## Azure DevOps Commands

All Azure DevOps commands support both CLI parameters and state-based execution.
Parameters passed via CLI are automatically persisted to state for reuse.

### Reply to PR Thread

```bash
# Option A: With CLI parameters (explicit, self-documenting)
agdt-reply-to-pull-request-thread --pull-request-id 23046 --thread-id 139474 --content "Your reply"
agdt-reply-to-pull-request-thread -p 23046 -t 139474 -c "Thanks!"

# Option B: Parameterless (uses current state)
agdt-set pull_request_id 23046
agdt-set thread_id 139474
agdt-set content "Your reply message"
agdt-reply-to-pull-request-thread

# Optionally resolve the thread after replying
agdt-set resolve_thread true
agdt-reply-to-pull-request-thread
```

### Add New PR Comment

```bash
# Option A: With CLI parameters (explicit)
agdt-add-pull-request-comment --pull-request-id 23046 --content "LGTM!"
agdt-add-pull-request-comment -p 23046 -c "Looks good"

# Option B: Parameterless (uses current state)
agdt-set pull_request_id 23046
agdt-set content "Your comment"
agdt-add-pull-request-comment

# For file-level comment
agdt-set path "src/example.py"
agdt-set line 42
agdt-add-pull-request-comment
```

### Approve Pull Request

```bash
# Option A: With CLI parameters
agdt-approve-pull-request --pull-request-id 23046 --content "Approved!"
agdt-approve-pull-request -p 23046

# Option B: Parameterless (uses current state)
agdt-set pull_request_id 23046
agdt-approve-pull-request
```

### Get PR Threads

```bash
# Option A: With CLI parameter
agdt-get-pull-request-threads --pull-request-id 23046
agdt-get-pull-request-threads -p 23046

# Option B: Parameterless (uses current state)
agdt-set pull_request_id 23046
agdt-get-pull-request-threads
```

### Resolve Thread

```bash
# Option A: With CLI parameters
agdt-resolve-thread --pull-request-id 23046 --thread-id 139474
agdt-resolve-thread -p 23046 -t 139474

# Option B: Parameterless (uses current state)
agdt-set pull_request_id 23046
agdt-set thread_id 139474
agdt-resolve-thread
```

### Dry Run Mode

```bash
agdt-set dry_run true
agdt-reply-to-pull-request-thread  # Previews without making API calls
```

## Azure Context Management

Manage multiple Azure CLI accounts (e.g., corporate account for Azure DevOps and AZA account for App Insights) without repeated `az login` / `az logout` cycles.

### Overview

The Azure context system uses separate `AZURE_CONFIG_DIR` directories per account context. Both accounts can stay authenticated simultaneously and can be switched instantly via environment variable.

**Available Contexts:**

- `devops` - Corporate account for Azure DevOps, Service Bus, etc.
- `resources` - AZA account for App Insights, Azure resources, Terraform, etc.

### Setup

1. **Switch to a context** (one-time setup per context):

```bash
# Switch to DevOps context
agdt-azure-context-use devops

# Switch to resources context
agdt-azure-context-use resources
```text

2. **Log in to each context** (one-time per context):

```bash
# After switching to a context, log in using Azure CLI
az login
# This login is stored in the context's isolated config directory
```text

### Usage

**Show all contexts with login status:**

```bash
agdt-azure-context-status
```text

Output:
```text
Azure CLI Contexts:
================================================================================

devops [ACTIVE]
  Description: Corporate account for Azure DevOps, Service Bus, etc.
  Config Dir:  ~/.azure-contexts/devops
  Status:      ✓ Logged in as user@company.com

resources
  Description: AZA account for App Insights, Azure resources, Terraform, etc.
  Config Dir:  ~/.azure-contexts/resources
  Status:      ✓ Logged in as user@company.com

================================================================================
```text

**Check current active context:**

```bash
agdt-azure-context-current
```text

**Switch contexts:**

```bash
# Switch to DevOps context
agdt-azure-context-use devops

# Switch to resources context
agdt-azure-context-use resources
```text

**Ensure logged in (prompts if needed):**

```bash
# Ensure current context is logged in
agdt-azure-context-ensure-login

# Ensure specific context is logged in
agdt-azure-context-ensure-login devops
```text

### How It Works

Each context uses its own isolated Azure CLI configuration directory:
- `~/.azure-contexts/devops/` - DevOps context config and tokens
- `~/.azure-contexts/resources/` - Resources context config and tokens

When you run `az` commands, the active context's `AZURE_CONFIG_DIR` is used, so both accounts stay authenticated simultaneously. Switching contexts is instant (no browser login flow).

### Integration

**With VPN toggle:**
Contexts work seamlessly with the VPN toggle system. When certain contexts require VPN, the system coordinates VPN state automatically.

**With Azure CLI:**
All `az` commands respect the active context automatically via the `AZURE_CONFIG_DIR` environment variable.

## Git Commands

The package provides streamlined Git workflow commands that support the
single-commit policy.

### Initial Commit & Publish

```bash
# Option A: With CLI parameter (explicit)
| `agdt-get-pull-request-threads` | Get all PR comment threads |

- Change 1
- Change 2

[DFLY-1234](https://jira.swica.ch/browse/DFLY-1234)"

# Option B: Parameterless (uses current state)
# Current commit_message: run `agdt-get commit_message` to check
agdt-git-save-work
```text

### Smart Commit (Auto-detects Amend)

The `agdt-git-save-work` command automatically detects if you're updating an
existing commit:

```bash
# First commit - creates new commit and publishes branch
agdt-git-save-work --commit-message "feature(DFLY-1234): initial implementation"

# Subsequent commits on same issue - automatically amends and force pushes
agdt-git-save-work --commit-message "feature(DFLY-1234): refined implementation

- Original changes
- Additional updates"
# Auto-detects and amends!
```text

**Detection logic:**

1. If branch has commits ahead of `origin/main` AND
2. Last commit message contains the current Jira issue key (from
   `jira.issue_key` state)
3. Then: amend existing commit and force push
4. Otherwise: create new commit and publish

### Individual Git Operations

```bash
agdt-git-stage       # Stage all changes (git add .)
agdt-git-push        # Push changes (git push)
agdt-git-force-push  # Force push with lease
agdt-git-publish     # Push with upstream tracking
```text

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
```text

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
```text

### Workflow Navigation

```bash
# View current workflow state
agdt-get-workflow

# Advance to next step
agdt-advance-workflow

# Clear workflow
agdt-clear-workflow
```text

## PyPI Release Commands

Verwende die `pypi.*` Namespace-Keys für Release-Parameter. Setze deine PyPI
Tokens via Umgebungsvariablen:

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
```text

### Status prüfen

```bash
agdt-task-status
agdt-task-log
agdt-task-wait
```text

## Jira Commands

All Jira commands use the `jira.*` namespace for state values. Set
`JIRA_COPILOT_PAT` environment variable with your Jira API token.

### Get Issue Details

```bash
agdt-set jira.issue_key "DFLY-1234"
agdt-get-jira-issue
```text

### Add Comment to Issue

Commands with optional CLI parameters support two usage patterns:

```bash
# Option A: With CLI parameters (explicit)
agdt-add-jira-comment --jira-comment "Your comment text"

# Option B: Parameterless (uses current state)
# Current jira.issue_key: run `agdt-get jira.issue_key` to check
# Current jira.comment: run `agdt-get jira.comment` to check
agdt-add-jira-comment
```text

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
```text

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
```text

### Create Subtask

```bash
agdt-set jira.parent_key "DFLY-1234"
agdt-set jira.summary "Subtask Title"
agdt-set jira.description "Subtask description"
agdt-create-subtask
```text

### Dry Run Mode for Jira

```bash
agdt-set jira.dry_run true
agdt-create-issue  # Previews payload without API call
```text

## VPN & Network Management

The corporate VPN (Pulse Secure/Ivanti) creates a full tunnel that blocks public registries (npm, PyPI) while being required for internal resources (Jira, ESB). These commands provide intelligent VPN management so you don't need to manually connect/disconnect VPN when switching between tasks.

### Network Status

Check your current network context:

```bash
agdt-network-status
```

Output shows:

- 🏢 Corporate network (in office) - VPN operations skipped automatically
- 🔌 Remote with VPN - Can access internal resources, external blocked
- 📡 Remote without VPN - Can access external resources, internal blocked

### Run Command with VPN Context

Automatically manage VPN based on command requirements:

```bash
# Ensure VPN is connected before running (for Jira, ESB, etc.)
agdt-vpn-run --require-vpn "curl https://jira.swica.ch/rest/api/2/issue/DP-123"

# Temporarily disconnect VPN for public access (npm, pip, etc.)
agdt-vpn-run --require-public "npm install"

# Auto-detect requirement from command content (default)
agdt-vpn-run --smart "az devops ..."
agdt-vpn-run "npm install express"  # --smart is the default
```

The command will:

- Detect if you're on corporate network (in office) and skip VPN operations
- Connect VPN if needed for internal resources
- Disconnect VPN temporarily for public registry access
- Restore VPN state after command completes

### Manual VPN Control

Direct VPN control commands (run in background):

```bash
# Connect VPN (skipped if on corporate network)
agdt-vpn-on
agdt-task-wait

# Disconnect VPN
agdt-vpn-off
agdt-task-wait

# Check VPN status
agdt-vpn-status
agdt-task-wait
```

### Common Workflows

**Install npm packages (needs public access):**

```bash
agdt-vpn-run --require-public "npm install"
```

**Access Jira API (needs VPN):**

```bash
agdt-vpn-run --require-vpn "curl https://jira.swica.ch/rest/api/2/serverInfo"
```

**Smart detection (recommended):**

```bash
# Auto-detects that npm install needs public access
agdt-vpn-run "npm install express lodash"

# Auto-detects that Jira URL needs VPN
agdt-vpn-run "curl https://jira.swica.ch/rest/api/2/issue/DP-123"
```

### In-Office Behavior

When on the corporate network (physically in the office), VPN operations are
automatically skipped since internal resources are already accessible. However,
note that the corporate network may still block external registries (npm, PyPI) -
in that case, consider connecting to a different network (e.g., mobile hotspot)
for external access.

## For Developers: Test Organization

All new unit tests follow the **1:1:1 policy** — one test file per symbol (function or class), mirroring the
source structure under `tests/unit/`. See [tests/README.md](tests/README.md) for the full
policy, rationale, and step-by-step guide.

**Quick reference:**

```text
tests/unit/{module_path}/{source_file_name}/test_{symbol_name}.py
```

Examples:

| Source | Test file |
|--------|-----------|
| `agentic_devtools/state.py` → `get_value()` | `tests/unit/state/test_get_value.py` |
| `agentic_devtools/cli/git/core.py` → `get_current_branch()` | `tests/unit/cli/git/core/test_get_current_branch.py` |

Run the structure validator before pushing:

```bash
python scripts/validate_test_structure.py
```

## Environment Variables

| Variable                         | Purpose                                                                             |
| -------------------------------- | ----------------------------------------------------------------------------------- |
| `AZURE_DEV_OPS_COPILOT_PAT`      | Azure DevOps PAT for API calls                                                      |
| `JIRA_COPILOT_PAT`               | Jira API token for authentication                                                   |
| `JIRA_BASE_URL`                  | Override default Jira URL (default: `https://jira.swica.ch`)                       |
| `JIRA_SSL_VERIFY`                | Set to `0` to disable SSL verification                                              |
| `JIRA_CA_BUNDLE`                 | Path to custom CA bundle PEM file for Jira SSL                                      |
| `REQUESTS_CA_BUNDLE`             | Standard requests library CA bundle path (fallback)                                 |
| `AGENTIC_DEVTOOLS_STATE_DIR`     | Override default state directory (e.g., `scripts/temp`)                             |
| `DFLY_AI_HELPERS_STATE_DIR`      | Legacy state directory override (still honored for backward compatibility)          |

## State File Location

By default, state is stored in `scripts/temp/agdt-state.json` (relative to the
repo root).

## Why This Design?

### Auto-Approval Friendly

VS Code's auto-approval matches exact command strings. By using:

- Generic `agdt-set key value` - approve once, use for any key
- Parameterless action commands like `agdt-reply-to-pr-thread`

...you only need to approve a few commands once, then they work for all future
operations.

### No Replacement Tokens Needed

Unlike PowerShell, Python's CLI parsing handles special characters natively:

```bash
# This just works!
agdt-set content "Code with (parentheses) and [brackets]"
```text

### No Multi-line Builder Needed

Python preserves multiline strings from the shell:

```bash
agdt-set content "Line 1
Line 2
Line 3"
```text

## GitHub Actions: SpecKit Issue Trigger

The repository includes a GitHub Action that automatically triggers the SpecKit
specification process when a `speckit` label is added to an issue.

### Visual Documentation

For a comprehensive visual representation of the complete workflow, see the
[SpecKit Workflow Sequence
Diagram](specs/002-github-action-speckit-trigger/workflow-sequence-diagram.md).
The diagram shows:

- All 8 workflow phases from initiation to completion
- Interactions between actors (User, GitHub, SpecKit Action, AI Provider,

  Repository)
  Repository)

- Decision points and error handling
- Integration with the Spec-Driven Development (SDD) pattern

### How It Works

1. Create a GitHub issue describing your feature
2. Add the `speckit` label to the issue (optionally assign it to Copilot or a
   team member)
3. The action posts an acknowledgment comment within 30 seconds
4. A feature specification is generated from the issue title and body
5. A new branch and pull request are created with the specification
6. Status comments are posted to the issue throughout the process

The `speckit` trigger label is automatically removed once processing starts,
and
replaced with status labels (`speckit:processing`, `speckit:completed`, or
`speckit:failed`).

### Configuration

Configure the action using repository variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `SPECKIT_TRIGG | `speckit` | The label that |
| `SPECKIT_AI_PR | `claude` | AI provider fo |
| `SPECKIT_COMMENT_ON_ISSUE` | `true` | Post status comments to the issue |
| `SPECKIT_CREATE_BRANCH` | `true` | Create a feature branch |
| `SPECKIT_CREATE_PR` | `true` | Create a pull request |

### Required Secrets

| Secret | Required For | Description |
|--------|--------------|-------------|
| `ANTHROPIC_API_KEY` | `claude` provider | Claude API key for spec generation |
| `OPENAI_API_KEY` | `openai` provider | OpenAI API key for spec generation |

### Usage

1. Create a GitHub issue with a descriptive title and body
2. Add the `speckit` label (or your configured trigger label)
3. Wait for the workflow to generate the specification
4. Review the generated spec in the pull request

### Manual Trigger

You can also trigger the workflow manually for testing:

```bash
gh workflow run speckit-issue-trigger.yml -f issue_number=123
```text

### Labels

The workflow uses labels to manage state:

- `speckit` - **Trigger label**: Add this to an issue to start specification

  generation
  generation

- `speckit:processing` - Specification generation in progress
- `speckit:completed` - Specification created successfully
- `speckit:failed` - Generation failed (check workflow logs)

## GitHub Actions: Security Scanning on Main Merge

The repository includes an automated security scanning workflow that runs whenever
code is merged to the main branch. This ensures continuous security monitoring and
helps identify vulnerabilities early.

### How It Works

1. Workflow triggers automatically on push to main branch (typically after PR merge)
2. Installs security scanning tools: `bandit`, `pip-audit`, `safety`
3. Runs comprehensive security scans:
   - **pip-audit**: Scans dependencies for known vulnerabilities (CVEs)
   - **bandit**: Static analysis for common security issues in Python code
   - **safety**: Checks dependencies against a database of known security issues
4. Creates a GitHub issue with the security scan report
5. Attaches scan reports as artifacts for detailed review

### Security Scan Report

After each merge to main, an issue is automatically created with:

- **Summary**: Quick overview of security status
- **Scan Results**: Findings from each security tool
- **Severity Breakdown**: Critical, high, medium, low issues
- **Next Steps**: Recommended actions to address findings
- **Artifacts**: Detailed JSON reports attached to the workflow run

### Labels

The workflow uses labels to categorize scan results:

- `security` - All security scan reports
- `security-scan` - Identifies automated scan issues
- `needs-review` - Findings detected, review required
- `all-clear` - No security issues detected

### Responding to Security Findings

When a security scan detects issues:

1. Review the created issue for summary of findings
2. Check workflow logs for detailed information
3. Download scan report artifacts for in-depth analysis
4. Address critical and high-severity issues immediately
5. Tag @copilot in the issue for assistance with remediation

### Manual Security Scan

You can manually trigger a security scan by running:

```bash
# Install security tools
pip install bandit safety pip-audit

# Run scans
pip-audit
bandit -r agentic_devtools
safety scan
```
