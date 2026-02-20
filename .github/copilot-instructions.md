# AI Agent Instructions: agentic-devtools Python Package

> Parent Instruction Chain
>
> 1. [Root global instructions](../../../.github/copilot-instructions.md)
> 2. [Scripts & Automation Navigation Hub](../../.github/copilot-instructions.md)
>
> [`copilot-instructions.md` Precedence Model](../../../docs/copilot-instructions-precedence-model.md)

## 1. Purpose

`agentic-devtools` is a pip-installable Python package that provides CLI commands for AI agents to interact with
Git, Azure DevOps, Jira, and other services. The design prioritizes **auto-approval** in VS Code by using:

- A generic `agdt-set key value` command (approve once, works for all keys)
- Parameterless action commands like `agdt-git-save-work`, `agdt-add-jira-comment`
- Native Python CLI handling of special characters and multiline content (no replacement tokens needed!)

### Copilot Chat Agents

Workflow steps can be started from VS Code Copilot Chat using `/agdt.<workflow>.<step>` commands.
Agents live in `.github/agents/` and prompts live in `.github/prompts/`, mirroring the
existing `speckit.*` pattern.

### Multi-Worktree Development

The package supports **multi-worktree development** where different worktrees can have different versions of `agentic-devtools`:

- **Smart Repo-Local Detection**: All `agdt-*` commands automatically detect the current git repo root and use the local `.agdt-venv` installation if present
- **Per-Worktree Isolation**: Each worktree can have its own version via `setup-dev-tools.py`, which creates a `.agdt-venv` with the local package installed
- **Graceful Fallback**: If no local venv exists, commands use the global pip installation
- **No Command Changes**: The same `agdt-*` commands work everywhere - the dispatcher handles routing automatically

**How it works:**

1. When you run any `agdt-*` command, the dispatcher checks `git rev-parse --show-toplevel`
2. It looks for `.agdt-venv/Scripts/python.exe` (Windows) or `.agdt-venv/bin/python` (Unix) at the repo root
3. If found, it re-executes the command using that Python interpreter
4. If not found, the command runs in the current Python environment

**Setting up a worktree with local helpers:**

```bash
# Run setup-dev-tools.py in the worktree
python setup-dev-tools.py

# This creates .agdt-venv with agentic-devtools installed from agentic_devtools/
# All agdt-* commands will now use this local version in this worktree
```

### Background Task Architecture

**All action commands** spawn background tasks and return immediately:

- Commands like `agdt-git-save-work`, `agdt-add-jira-comment`, `agdt-create-pull-request` run in the background
- They return immediately with a task ID for tracking
- Results are written to output files in `scripts/temp/` when the task completes
- Use `agdt-task-status`, `agdt-task-log`, or `agdt-task-wait` to monitor progress
- The immediate console output tells the AI agent:
  1. What background task was triggered
  2. The task ID for status checking
  3. Where to find results when complete (output file path)

### ⚠️ CRITICAL: Testing Commands

**When working on `agentic-devtools`, ALWAYS use `agdt-test` commands - NEVER run pytest directly!**

```bash
# Full test suite (background, ~55 seconds for 2000+ tests)
agdt-test
agdt-task-wait

# Quick tests without coverage (background)
agdt-test-quick
agdt-task-wait

# Specific source file with 100% coverage requirement (background)
agdt-test-file --source-file agentic_devtools/state.py  # Auto-saves to state
agdt-task-wait

# Specific test - synchronous (simpler for quick checks)
agdt-test-pattern tests/test_jira_helpers.py::TestClassName -v
```

Why:

- Tests run as background tasks to prevent AI agents from thinking something went wrong
- Logs are captured properly in `scripts/temp/background-tasks/logs/`
- Direct pytest calls don't integrate with the background task system
- `agdt-test-file` shows coverage ONLY for the specified source file

See [Testing](#12-testing) for all test commands.

## 2. Package Structure

```text
agentic_devtools/
├── __init__.py          # Package metadata
├── state.py             # JSON state management (single file: agdt-state.json)
├── file_locking.py      # Cross-platform file locking for state
├── task_state.py        # Background task state schema and CRUD
├── background_tasks.py  # Background task execution infrastructure
├── cli/
│   ├── __init__.py
│   ├── state.py         # Generic set/get/delete/clear/show commands
│   ├── azure_devops/    # Azure DevOps module (modular package)
│   │   ├── __init__.py  # Re-exports public API for backward compatibility
│   │   ├── config.py    # Constants + AzureDevOpsConfig dataclass
│   │   ├── auth.py      # PAT and auth header functions
│   │   ├── helpers.py   # Pure utility functions (no state reading)
│   │   └── commands.py  # CLI commands with dry_run + state reading
│   ├── git/             # Git workflow commands (package)
│   │   ├── __init__.py  # Command exports
│   │   ├── core.py      # State helpers, git execution, temp files
│   │   ├── operations.py # Individual git operations
│   │   └── commands.py  # CLI entry points
│   ├── jira/            # Jira commands (package)
│   │   ├── __init__.py  # Command exports
│   │   ├── config.py    # Jira configuration and auth
│   │   ├── commands.py  # Synchronous CLI entry points
│   │   ├── update_commands.py # Issue update command
│   │   └── async_commands.py  # Background/async command wrappers
│   └── tasks/           # Background task monitoring (package)
│       ├── __init__.py  # Command exports
│       └── commands.py  # Task monitoring CLI commands
├── prompts/             # Prompt template system (package)
│   ├── __init__.py      # Package exports
│   └── loader.py        # Template loading, validation, substitution
└── pyproject.toml       # Package config with entry points
```

### Module Responsibilities

| Module | Responsibility |
|--------|---------------|
| `azure_devops/config.py` | Constants (`DEFAULT_ORGANIZATION`, `APPROVAL_SENTINEL`, etc.) and `AzureDevOpsConfig` dataclass |
| `azure_devops/auth.py` | `get_pat()` and `get_auth_headers()` for Azure DevOps authentication |
| `azure_devops/helpers.py` | Pure utility functions: `build_thread_context`, `convert_to_pull_request_title`, `format_approval_content`, `verify_az_cli`, etc. |
| `azure_devops/commands.py` | CLI entry points: `reply_to_pull_request_thread`, `add_pull_request_comment`, `create_pull_request`, `resolve_thread`, `get_pull_request_threads`, `approve_pull_request` |
| `azure_devops/file_review_commands.py` | File-level review: `approve_file`, `request_changes`, `request_changes_with_suggestion`, `submit_file_review` - includes marking as reviewed and queue management |
| `azure_devops/mark_reviewed.py` | Mark files as reviewed in Azure DevOps: updates Reviewers API and Contribution API for UI display |
| `azure_devops/review_commands.py` | PR review workflow: `review_pull_request`, prompt generation, Jira integration |
| `azure_devops/__init__.py` | Re-exports all public API for backward compatibility (`from agentic_devtools.cli.azure_devops import reply_to_pr_thread`) |
| `git/core.py` | State helpers, git command execution, temp file handling |
| `git/operations.py` | Individual git operations (stage, commit, push, etc.) and smart amend detection |
| `git/commands.py` | CLI entry points: `agdt-git-save-work` (auto-detects amend), `agdt-git-stage`, `agdt-git-push`, etc. |
| `prompts/loader.py` | Template loading, variable extraction, validation, substitution, and output saving |
| `cli/workflows/base.py` | Base workflow utilities: `validate_required_state`, `initiate_workflow`, `advance_workflow_step` |
| `cli/workflows/commands.py` | Workflow initiation CLI commands for each workflow type |
| `cli/workflows/preflight.py` | Pre-flight checks for work-on-jira-issue: worktree/branch validation |
| `cli/workflows/advancement.py` | Auto-advancement helpers called by other commands to progress workflows |

## 3. State Management Pattern

All state is stored in a single JSON file (`scripts/temp/agdt-state.json`):

```python
from agentic_devtools.state import get_value, set_value, load_state

# Set values
set_value("pr_id", 23046)
set_value("content", "My reply message")

# Get values
pr_id = get_value("pr_id")
content = get_value("content")

# Load entire state
state = load_state()  # Returns dict
```

### Workflow State

Workflow state is stored separately under the `_workflow` key and managed through dedicated functions:

```python
from agentic_devtools.state import (
    get_workflow_state, set_workflow_state, clear_workflow_state,
    is_workflow_active, update_workflow_step, update_workflow_context
)

# Set workflow state
set_workflow_state(
    name="pull-request-review",
    status="active",
    step="initiate",
    context={"pull_request_id": "123"}
)

# Check if a workflow is active
if is_workflow_active():
    workflow = get_workflow_state()
    print(f"Active: {workflow['name']} at step {workflow['step']}")

# Update workflow progress
update_workflow_step("reviewing")
update_workflow_context(files_reviewed=5)

# Clear when done
clear_workflow_state()
```

### Workflow Transition Behavior

Workflows advance through steps via event-driven transitions. The transition behavior depends on the `auto_advance` flag and `required_tasks`:

1. **Immediate Advancement** (auto_advance=True, no required_tasks):
   - The workflow step changes immediately
   - The next step's prompt is rendered and printed to the console
   - Examples: `CHECKLIST_CREATED`, `CHECKLIST_COMPLETE`, `JIRA_COMMENT_ADDED`

2. **Deferred Advancement** (auto_advance=True, has required_tasks):
   - A `pending_transition` is recorded in the workflow context
   - The step changes when `agdt-get-next-workflow-prompt` is called AND the background tasks complete
   - Examples: `GIT_COMMIT_CREATED` (waits for agdt-git-commit task)

3. **Manual Advancement** (auto_advance=False):
   - Requires explicit `agdt-advance-workflow` command
   - Used for steps that need human confirmation

When a transition fires immediately, the output looks like:

```text
================================================================================
WORKFLOW ADVANCED: work-on-jira-issue
NEW STEP: implementation-review
================================================================================

# Work on Jira Issue - Implementation Review Step
...
```

### Jira Namespace

Jira commands use keys prefixed with `jira.`:

```bash
agdt-set jira.issue_key DFLY-1234
agdt-set jira.comment "My comment"
```

## 4. CLI Commands

### State Management

| Command | Purpose | Example |
|---------|---------|---------|
| `agdt-set` | Set any key-value | `agdt-set pull_request_id 23046` |
| `agdt-get` | Get a value | `agdt-get content` |
| `agdt-delete` | Remove a key | `agdt-delete thread_id` |
| `agdt-clear` | Clear all state | `agdt-clear` |
| `agdt-show` | Show all state | `agdt-show` |

### Azure DevOps Actions (Background Tasks)

All action commands that mutate state or perform API calls spawn background tasks and return immediately with a task ID for tracking.

| Command | Purpose | Required State / CLI Args |
|---------|---------|---------------------------|
| `agdt-add-pull-request-comment` | Add new PR comment | pull_request_id, content |
| `agdt-approve-pull-request` | Approve PR with sentinel banner | pull_request_id, content |
| `agdt-create-pull-request` | Create a new pull request | source_branch, title OR `--source-branch`, `--title`, `--description` |
| `agdt-reply-to-pull-request-thread` | Reply to PR thread | pull_request_id, thread_id, content |
| `agdt-resolve-thread` | Resolve a PR thread | pull_request_id, thread_id |
| `agdt-mark-pull-request-draft` | Mark PR as draft | pull_request_id |
| `agdt-publish-pull-request` | Publish draft PR | pull_request_id |
| `agdt-run-e2e-tests` | Trigger E2E test pipeline | (pipeline params) |
| `agdt-run-wb-patch` | Trigger workbench patch pipeline | (pipeline params) |
| `agdt-review-pull-request` | Start PR review workflow | (optional) pull_request_id, jira.issue_key |
| `agdt-generate-pr-summary` | Generate PR summary comments | pull_request_id |

**Create Pull Request CLI Parameter Support:**

```bash
# Option A: With CLI parameters (explicit)
agdt-create-pull-request --source-branch "feature/DFLY-1234/new-feature" --title "feature(DFLY-1234): add new feature" --description "Description here"

# Option B: Parameterless (uses current state)
# Check current values: agdt-get source_branch, agdt-get title
agdt-create-pull-request
```

### Azure DevOps Query Commands (Background Tasks)

Query commands also spawn background tasks - results are written to output files:

| Command | Purpose | Required State | Output File |
|---------|---------|----------------|-------------|
| `agdt-get-pull-request-threads` | Get all PR comment threads | pull_request_id | `temp/pr-threads-{pr_id}.json` |
| `agdt-get-pull-request-details` | Get full PR details (diff, threads, iterations) | pull_request_id | `temp/pr-details-{pr_id}.json` |
| `agdt-get-run-details` | Get pipeline/build run details | run_id | `temp/run-details-{run_id}.json` |

### Pull Request Review Commands (Background Tasks)

| Command | Purpose | Required State / CLI Args |
|---------|---------|---------------------------|
| `agdt-review-pull-request` | Start PR review workflow | (optional) pull_request_id or jira.issue_key |
| `agdt-approve-file` | Approve a file during review | pull_request_id, file_review.file_path, content OR `--file-path`, `--content`, `--pull-request-id` |
| `agdt-request-changes` | Request changes on a file | pull_request_id, file_review.file_path, content, line OR `--file-path`, `--content`, `--line`, `--pull-request-id` |
| `agdt-request-changes-with-suggestion` | Request changes with code suggestion | pull_request_id, file_review.file_path, content, line OR `--file-path`, `--content`, `--line`, `--pull-request-id` |
| `agdt-mark-file-reviewed` | Mark a file as reviewed (standalone) | pull_request_id, file_review.file_path |
| `agdt-submit-file-review` | Submit batched file review | pull_request_id |

**File Review CLI Parameter Support:**

File review commands accept optional CLI arguments that override state values:

```bash
# Option A: With CLI parameters (explicit, self-documenting)
agdt-approve-file --file-path "src/app/component.ts" --content "LGTM - clean implementation"
agdt-request-changes --file-path "src/app/service.ts" --content "Missing null check" --line 42
agdt-request-changes-with-suggestion --file-path "src/utils.ts" --content "```suggestion
const value = x ?? defaultValue;
```" --line 15

# Option B: Parameterless (uses current state)
# Check current values: agdt-get file_review.file_path, agdt-get content, agdt-get line
agdt-approve-file
agdt-request-changes
```

**Review Command Behavior:**

All file review commands automatically:

1. Post the review comment (runs as background task)
2. Mark the file as reviewed in Azure DevOps (visible as "viewed" eye icon in PR UI)
3. Update the review queue (`queue.json`)
4. Print next steps (continue with next file or generate summary)

### Git Workflow Actions (Background Tasks)

All Git workflow commands spawn background tasks:

| Command | Purpose | Required State |
|---------|---------|----------------|
| `agdt-git-save-work` | Stage, commit/amend, publish/force-push | commit_message |
| `agdt-git-stage` | Stage all changes | (none) |
| `agdt-git-push` | Push to origin | (none) |
| `agdt-git-force-push` | Force push to origin | (none) |
| `agdt-git-publish` | Publish branch upstream | (none) |

**Smart Commit Detection:**
The `agdt-git-save-work` command automatically detects whether to create a new commit or amend:

- If branch has commits ahead of `origin/main` AND last commit contains current issue key → **amend + force push**
- Otherwise → **new commit + publish**

**Checklist Integration:**
Use `--completed` to mark checklist items during commit:

```bash
agdt-git-save-work --completed 1 2 3  # Marks items 1, 2, 3 complete before committing
```

**Optional Git state keys:**

- `dry_run` - Preview operations without executing
- `skip_stage` - Skip the staging step
- `skip_publish` - Skip branch publish after initial commit

### Jira Actions (Background Tasks)

All Jira action commands that mutate state spawn background tasks:

| Command | Purpose | Required State / CLI Args |
|---------|---------|---------------------------|
| `agdt-add-jira-comment` | Add comment to issue | `jira.issue_key`, `jira.comment` OR `--jira-comment`, `--jira-issue-key` |
| `agdt-update-jira-issue` | Update issue fields | jira.issue_key, plus field keys |
| `agdt-create-epic` | Create a new epic | jira.project_key, jira.summary, jira.epic_name, jira.role, jira.desired_outcome, jira.benefit |
| `agdt-create-issue` | Create a new issue | jira.project_key, jira.summary, jira.description (or role/outcome/benefit) |
| `agdt-create-subtask` | Create a subtask | jira.parent_key, jira.summary, jira.description |

**CLI Parameter Support:**
Some commands accept optional CLI arguments that override state values:

- `agdt-add-jira-comment --jira-comment "..." [--jira-issue-key KEY]` - Comment text and issue key can be passed directly
- When CLI args are provided, they are stored in state before execution

**Documentation Pattern for Commands with Optional Parameters:**

When documenting commands that support both CLI parameters and parameterless execution, show both options:

```bash
# Option A: With CLI parameters (explicit)
agdt-add-jira-comment --jira-comment "Your comment text here"

# Option B: Parameterless (uses current state)
# Current jira.issue_key: run `agdt-get jira.issue_key` to check
# Current jira.comment: run `agdt-get jira.comment` to check
agdt-add-jira-comment
```

This pattern:

1. Shows CLI parameters first for explicit, self-documenting usage
2. Shows parameterless alternative that uses current state values
3. Indicates how to check current state values before running parameterless

### Jira Role Management (Background Tasks)

| Command | Purpose | Required State |
|---------|---------|----------------|
| `agdt-list-project-roles` | List project roles | jira.project_key |
| `agdt-get-project-role-details` | Get role details | jira.project_key, jira.role_id |
| `agdt-add-users-to-project-role` | Add users to role | jira.project_key, jira.role_id, jira.usernames |
| `agdt-add-users-to-project-role-batch` | Batch add users | jira.project_key, jira.role_id, jira.usernames |
| `agdt-find-role-id-by-name` | Find role ID | jira.project_key, jira.role_name |
| `agdt-check-user-exists` | Check if user exists | jira.username |
| `agdt-check-users-exist` | Check multiple users | jira.usernames |

### Jira Query Commands (Background Tasks)

Jira query commands also spawn background tasks - results are written to output files:

| Command | Purpose | Required State | Output File |
|---------|---------|----------------|-------------|
| `agdt-get-jira-issue` | Get issue details | jira.issue_key | `temp/temp-get-issue-details-response.json` |
| `agdt-parse-jira-error-report` | Parse error report | (file input) | `temp/jira-error-report.json` |

**`agdt-get-jira-issue` Features:**

- **Automatic subtask detection**: Checks `issuetype.subtask` field
- **Automatic parent retrieval**: Fetches parent issue for subtasks → `temp/temp-get-parent-issue-details-response.json`
- **Automatic epic retrieval**: Fetches linked epic via `customfield_10008` → `temp/temp-get-epic-details-response.json`
- **Metadata references in state**: Stores file locations and timestamps, NOT full JSON:
  - `jira.issue_details` → `{location, retrievalTimestamp}`
  - `jira.parent_issue_details` → `{location, key, retrievalTimestamp}` (if subtask)
  - `jira.epic_details` → `{location, key, retrievalTimestamp}` (if epic linked)
- **Console output**: Prints formatted issue details including parent/epic info

**Update Issue State Keys:**

- `jira.summary` - New summary text
- `jira.description` - New description text
- `jira.labels` - Comma-separated labels (replaces existing)
- `jira.labels_add` - Comma-separated labels to add
- `jira.labels_remove` - Comma-separated labels to remove
- `jira.assignee` - Username to assign (empty string to unassign)
- `jira.priority` - Priority name (e.g., "High", "Medium", "Low")
- `jira.custom_fields` - JSON object of custom field IDs to values

### Background Task Management

| Command | Purpose | Required State |
|---------|---------|----------------|
| `agdt-tasks` | List all background tasks | (none) |
| `agdt-task-status` | Show detailed task status | background.task_id |
| `agdt-task-log` | Display task output log | background.task_id |
| `agdt-task-wait` | Wait for task completion | background.task_id |
| `agdt-tasks-clean` | Clean up expired tasks | (none) |

**Optional Background Task State Keys:**

- `background.task_id` - Task ID to query/wait for
- `background.timeout` - Wait timeout in seconds (default: 300)
- `background.poll_interval` - Poll interval in seconds (default: 2)
- `background.log_lines` - Number of log lines to show (negative for tail)
- `background.expiry_hours` - Hours before tasks expire (default: 24)

**Background Task Pattern:**

Action commands spawn background processes and return immediately:

```bash
# Start background operation
agdt-set jira.issue_key DFLY-1234
agdt-set jira.comment "Processing complete"
agdt-add-jira-comment
# Output: Background task started: <task-id>

# Monitor the task
agdt-set background.task_id <task-id>
agdt-task-status   # Check current status
agdt-task-log      # View output log
agdt-task-wait     # Wait for completion
```

### Testing Actions

**⚠️ CRITICAL FOR AI AGENTS: ALWAYS use these agdt-test commands, NEVER run pytest directly!**

These commands run tests in BACKGROUND TASKS and return immediately with a task ID.
The test suite has 2000+ tests and takes ~55 seconds - running synchronously causes
AI agents to think something went wrong and restart tests multiple times.

| Command | Purpose | Required State |
|---------|---------|----------------|
| `agdt-test` | Run full test suite with coverage (~55s) | (none) |
| `agdt-test-quick` | Run tests without coverage (faster) | (none) |
| `agdt-test-file --source-file <path>` | Run tests for a specific source file with 100% coverage | (none - uses `--source-file` param) |
| `agdt-test-pattern <args>` | Run specific tests (SYNCHRONOUS) | (none - takes args) |

**Basic workflow (full test suite):**

```bash
# Run tests in background
agdt-test

# Wait for completion (REQUIRED - do not skip!)
agdt-task-wait
```

**Running tests for a specific source file (with focused coverage):**

```bash
# Specify source file via --source-file (auto-saved to state for future runs)
agdt-test-file --source-file agentic_devtools/state.py
agdt-task-wait
```

This is ideal when working on a single module and wanting to ensure full test coverage.
The command:

- Infers the test file from the source file name (e.g., `state.py` → `test_state.py`)
- Shows coverage ONLY for the specified source file (not the entire codebase)
- Requires 100% coverage for the target file to pass
- Auto-saves `--source-file` to state, so subsequent runs can omit the parameter

**Running specific test classes or methods (synchronous):**

```bash
# Test a specific class
agdt-test-pattern tests/test_jira_helpers.py::TestEnsureJiraPem -v

# Test a specific method
agdt-test-pattern "tests/test_state.py::TestWorkflowState::test_set_and_get_workflow_state" -v
```

**When to use which command:**

- `agdt-test` - Full suite validation before committing (required!)
- `agdt-test-quick` - Full suite without coverage for faster iteration
- `agdt-test-file` - Background execution for specific file/pattern (use when you want to check other things while tests run)
- `agdt-test-pattern` - Synchronous execution when you need immediate results from a specific test

**DO NOT:**

- Run `pytest` directly
- Run multiple test commands in parallel
- Assume tests failed if command returns quickly (they run in background)

### Workflow Management

| Command | Purpose | Required State |
|---------|---------|----------------|
| `agdt-get-workflow` | Display current workflow state | (none) |
| `agdt-clear-workflow` | Clear workflow state | (none) |
| `agdt-create-checklist` | Create checklist from CLI args | (none - takes args) |
| `agdt-update-checklist` | Update checklist items | (checklist in workflow) |
| `agdt-show-checklist` | Display current checklist | (checklist in workflow) |

### Workflow Initiation Commands

These commands initiate a workflow, loading and rendering the appropriate prompt template:

| Command | Purpose | Required Parameters |
|---------|---------|---------------------|
| `agdt-initiate-pull-request-review-workflow` | Start PR review workflow | `--pull-request-id` or `--issue-key` |
| `agdt-initiate-work-on-jira-issue-workflow` | Start work on Jira issue | `--issue-key` |
| `agdt-initiate-create-jira-issue-workflow` | Start create issue workflow | `--project-key` |
| `agdt-initiate-create-jira-epic-workflow` | Start create epic workflow | `--project-key` |
| `agdt-initiate-create-jira-subtask-workflow` | Start create subtask workflow | `--parent-key` |
| `agdt-initiate-update-jira-issue-workflow` | Start update issue workflow | `--issue-key` |
| `agdt-initiate-apply-pr-suggestions-workflow` | Apply PR review suggestions | `--pull-request-id` |
| `agdt-advance-workflow` | Advance to next workflow step | (active workflow) |

**Workflow Command Behavior:**

1. Validates required state keys are present
2. Collects variables from state (both required and optional)
3. Loads the appropriate prompt template (override if exists, else default)
4. Validates override template doesn't introduce new variables
5. Substitutes variables into the template
6. Saves the rendered prompt to `scripts/temp/temp-<workflow>-<step>-prompt.md`
7. Logs the prompt to console with a notice of where it was saved
8. Updates workflow state (name, status=active, step, context)

### Work-on-Jira-Issue Workflow (State Machine)

The `agdt-initiate-work-on-jira-issue-workflow` uses an enhanced state-machine approach:

**Pre-flight Checks:**

1. Validates that the current folder contains the issue key (case-insensitive)
2. Validates that the current git branch contains the issue key
3. If either check fails → outputs setup instructions with worktree/branch commands

**Steps:**

1. **setup** - If pre-flight fails: instructions to create worktree and branch
2. **retrieve** - Auto-fetches Jira issue details via `agdt-get-jira-issue`
3. **planning** - Analyze issue and post plan comment to Jira
4. **checklist-creation** - Create implementation checklist based on plan
5. **implementation** - Code changes, tests, documentation (with checklist tracking)
6. **implementation-review** - Review completed checklist before verification
7. **verification** - Run tests and quality gates
8. **commit** - Stage and commit changes
9. **pull-request** - Create PR
10. **completion** - Post final Jira comment

**Automatic Workflow Advancement:**

- `agdt-add-jira-comment` advances from `planning` → `checklist-creation`
- `agdt-create-checklist` advances from `checklist-creation` → `implementation`
- When all checklist items are complete → advances to `implementation-review`
- `agdt-git-save-work` advances from `commit` → `pull-request`
- `agdt-create-pull-request` advances from `pull-request` → `completion`

### Checklist Management Commands

| Command | Purpose | Required State |
|---------|---------|----------------|
| `agdt-create-checklist` | Create checklist from CLI args | (none - takes args) |
| `agdt-update-checklist` | Update checklist items | (checklist in workflow) |
| `agdt-show-checklist` | Display current checklist | (checklist in workflow) |

**Usage:**

```bash
# Create checklist
agdt-create-checklist "Implement domain model" "Add tests" "Update docs"

# Mark items as complete
agdt-update-checklist --completed 1 2

# View checklist
agdt-show-checklist

# Mark items complete during commit
agdt-git-save-work --completed 1 2 3
```

**Manual Advancement:**

```bash
# Advance to a specific step
agdt-advance-workflow implementation
agdt-advance-workflow verification
agdt-advance-workflow commit

# View current step
agdt-get-workflow
```

**Usage Examples:**

```bash
# Start work on a Jira issue
agdt-set jira.issue_key DFLY-1234
agdt-initiate-work-on-jira-issue-workflow
# If pre-flight fails: shows worktree/branch setup instructions
# If pre-flight passes: auto-fetches issue and shows planning prompt

# Check current workflow
agdt-get-workflow
# Output: name=work-on-jira-issue, status=in-progress, step=planning

# Post plan comment (auto-advances to implementation)
agdt-set jira.comment "h4. Plan..."
agdt-add-jira-comment

# Advance manually when needed
agdt-advance-workflow verification

# Clear workflow when done
agdt-clear-workflow
```

**Usage examples:**

```bash
# ⚠️ ALWAYS use agdt-test commands, NEVER pytest directly!

# Full suite with coverage (runs in background, ~55 seconds)
agdt-test
agdt-task-wait   # REQUIRED: Wait for completion

# Quick run without coverage (runs in background)
agdt-test-quick
agdt-task-wait

# Specific file, class, or test via CLI argument (runs synchronously)
agdt-test-pattern tests/test_jira_helpers.py::TestEnsureJiraPem
agdt-test-pattern tests/test_jira_helpers.py::TestEnsureJiraPem::test_returns_existing_pem_path

# Test a specific source file with 100% coverage (runs in background)
agdt-test-file --source-file agentic_devtools/state.py  # Auto-saved to state
agdt-task-wait   # REQUIRED: Wait for completion
```

## 5. Key Design Decisions

### No Replacement Tokens

Unlike PowerShell, Python CLI handles special characters natively:

```bash
# This just works - no token replacement needed!
agdt-set content "Code with (parentheses) and [brackets]"
```

### No Multi-line Builder

Python preserves multiline strings directly:

```bash
agdt-set content "Line 1
Line 2
Line 3"
```

### Generic Setter Pattern

The `agdt-set` command accepts any key, so AI agents only need to approve it once:

```bash
agdt-set pr_id 12345       # Same command pattern
agdt-set thread_id 67890   # Same command pattern
agdt-set content "text"    # Same command pattern
```

## 6. Prompt Template System

Workflow commands use a template system for generating prompts:

### Template Location

- **Default templates**: `agentic_devtools/prompts/default-<step>-<workflow>-prompt.md`
- **Override templates**: `agentic_devtools/prompts/override-<step>-<workflow>-prompt.md`
- **Generated output**: `scripts/temp/temp-<workflow>-<step>-prompt.md`

### Template Variables

Templates use `{{variable_name}}` syntax for substitution:

```markdown
# Working on {{jira_issue_key}}

You are working on Jira issue **{{jira_issue_key}}**.
```

Variables are populated from state, with dot notation converted to underscores:

- State key `jira.issue_key` → Template variable `{{jira_issue_key}}`
- State key `pull_request_id` → Template variable `{{pull_request_id}}`

### Override Templates

Users can create override templates to customize workflow prompts:

1. Copy the default template to an override file
2. Modify as needed
3. **Important**: Override templates cannot introduce new variables not present in the default

Example validation error:

```text
TemplateValidationError: Override template uses variables not in default: {'new_variable'}
```

### Creating Custom Workflows

To add a new workflow:

1. Create the default prompt template in `agentic_devtools/prompts/`
2. Add the workflow initiation function in `cli/workflows/commands.py`
3. Export the function in `cli/workflows/__init__.py`
4. Add the CLI entry point in `pyproject.toml`
5. Document the required state keys

## 7. Installation

```bash
# From the package directory (scripts/agentic_devtools)
pip install -e .

# Or with dev dependencies
pip install -e ".[dev]"
```

### Multi-Worktree State Isolation

When working with multiple git worktrees (e.g., one for feature development and another for the main branch),
the `agdt-ai-helpers` package uses **smart repo-local state detection** to keep state isolated per worktree.

**How it works:**

1. State files are stored in `scripts/temp/` relative to the repository/worktree root
2. The `get_state_dir()` function walks up from the current directory looking for a `scripts` directory
3. Once found, it automatically creates `scripts/temp/` if it doesn't exist
4. This ensures each worktree has its own isolated state, even with a single global pip installation

**State directory resolution priority:**

1. `AGENTIC_DEVTOOLS_STATE_DIR` environment variable (explicit override)
2. `scripts/temp/` relative to repo root (auto-detected and created if needed)
3. `.agdt-temp/` in current working directory (fallback for non-repo contexts)

**New worktree setup:**
When creating a new worktree, `scripts/temp/` doesn't exist initially (it's gitignored). The helpers automatically create it on first use, so no manual setup is required.

**Tip:** Use the `agdt-initiate-work-on-jira-issue-workflow` command which includes worktree setup automation with VS Code integration.

## 8. Environment Variables

| Variable | Purpose |
|----------|---------||
| `AZURE_DEV_OPS_COPILOT_PAT` | PAT for Azure DevOps API calls |
| `JIRA_COPILOT_PAT` | PAT for Jira API calls |
| `JIRA_BASE_URL` | Override default Jira URL (default: `https://jira.swica.ch`) |
| `JIRA_SSL_VERIFY` | Set to "0" to disable SSL verification |
| `JIRA_CA_BUNDLE` | Path to custom CA bundle PEM file for Jira SSL |
| `REQUESTS_CA_BUNDLE` | Standard requests library CA bundle path (fallback) |
| `AGENTIC_DEVTOOLS_STATE_DIR` | Override default state directory (scripts/temp) |
| `DFLY_DRY_RUN` | Set to "1" for dry-run mode globally |

### SSL Certificate Handling

The Jira commands automatically handle SSL certificate verification for corporate internal CAs:

1. **Environment override**: Set `JIRA_SSL_VERIFY=0` to disable verification entirely
2. **Custom CA bundle**: Set `JIRA_CA_BUNDLE` to a path containing your CA certificates
3. **Repo-committed bundle**: The preferred CA bundle is committed at `scripts/jira_ca_bundle.pem` (contains the full certificate chain for jira.swica.ch)
4. **Auto-fetch fallback**: If the repo bundle doesn't exist, certificates are auto-fetched from the Jira server using `openssl s_client` and cached to `scripts/temp/jira_ca_bundle.pem`
5. **Last resort**: If auto-fetch fails, SSL verification is disabled with a warning

## 9. Adding New Commands

### Adding a new action command (background task pattern)

When adding a new command that performs side effects (API calls, git operations, file mutations):

1. **Add the sync function** in the appropriate module (e.g., `cli/azure_devops/commands.py`)
2. Read required state with `get_value()` or use existing helper functions like `parse_bool_from_state()`
3. Export the function in the module's `__init__.py`
4. **Create an async wrapper** that uses `run_in_background()` to spawn the sync command as a background task
5. **Add entry point** in `pyproject.toml`:

   ```toml
   [project.scripts]
   agdt-new-command = "agentic_devtools.cli.module.commands:new_command_async"
   ```

6. Reinstall: `pip install -e .`
7. **Document the command** in this file

### Adding new helper functions

1. Add pure utility functions (no state reading) to `cli/azure_devops/helpers.py`
2. Add functions that read state to `cli/azure_devops/commands.py`
3. Export in `__init__.py` if needed for external use

### Adding convenience state functions

Add typed functions in `state.py`:

```python
def get_new_field(required: bool = False) -> Optional[str]:
    """Get the new field from state."""
    return get_value("new_field", required=required)
```

## 10. Protected / Auto-Generated Files

> **⚠️ AI AGENTS: Never edit, stage, or commit the files listed here.**
> They are auto-generated at build time. Any local changes are noise and must be discarded.

### `agentic_devtools/_version.py`

Generated automatically by `hatch-vcs` / `setuptools-scm` from Git tags. Its header reads:
_"file generated by setuptools-scm — don't change, don't track in version control."_

The file is listed in `.gitignore`. **Do not** `git add`, edit, or commit it.

- To bump the package version, create a new Git tag — see [RELEASING.md](../RELEASING.md).
- If you see it modified in `git status`, discard it: `git checkout -- agentic_devtools/_version.py`

### Identifying auto-generated files in the future

A file is auto-generated when it contains a comment such as:

```text
# file generated by <tool>
# don't change, don't track in version control
```

When you encounter such a comment in a file you are about to edit or commit, **stop** — the file
should not be touched manually.

### Excluding auto-generated files from source-scanning tools

Any script that iterates over `agentic_devtools/` source files (e.g., `scripts/scaffold_tests.py`)
must **explicitly exclude** `_version.py` by name, in addition to `__init__.py`. Even though
`_version.py` currently has no public functions, the exclusion makes the intent clear and prevents
the file from accidentally appearing in generated output if it ever gains a public symbol.

Pattern to follow:

```python
if p.name not in {"__init__.py", "_version.py"} and "__pycache__" not in p.parts
```

## 11. Python Coding Patterns

### Import ordering (ruff/isort)

Ruff enforces isort-style import ordering (rule set `I`). All Python files must use this order:

1. **Standard library** imports
2. **Third-party** imports (e.g., `pytest`, `requests`)
3. **First-party** imports (`agentic_devtools.*`, `agdt_ai_helpers.*`)

Within each group, `import X` lines come before `from X import Y` lines.

```python
# Correct
import os
import time
from unittest.mock import patch   # stdlib — same group as os/time

import pytest                     # third-party

from agentic_devtools.state import get_value  # first-party
```

```python
# Wrong — stdlib 'from unittest.mock import patch' placed after third-party 'import pytest'
import pytest
from unittest.mock import patch   # ← ruff I001 violation
```

To auto-fix: `ruff check --fix tests/` or `ruff check --fix --select I tests/`

### Dynamic script loading with `importlib`

When loading a script dynamically (e.g., loading a `scripts/*.py` file by path), always guard
against `None` returns from `spec_from_file_location()` before calling `module_from_spec()` and
`exec_module()`:

```python
import importlib.util

spec = importlib.util.spec_from_file_location("module_name", script_path)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load module from {script_path!s}")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
```

`spec_from_file_location()` returns `None` when the file cannot be found or the path is not
recognised as a loadable Python source. Without the guard, the very first call — `module_from_spec(spec)`
— raises an obscure `AttributeError: 'NoneType' object has no attribute ...` that hides the real
problem. The explicit `RuntimeError` surfaces the actual path that failed, making failures
trivially easy to diagnose.

## 12. Testing

**⚠️ AI AGENTS: ALWAYS use agdt-test commands, NEVER pytest directly!**

```bash
# Run tests (ALWAYS use these commands)
agdt-test          # Full suite with coverage (background, ~55s)
agdt-task-wait     # Wait for completion (REQUIRED!)

agdt-test-quick    # Fast run without coverage (background)
agdt-task-wait     # Wait for completion (REQUIRED!)

# For specific tests (with CLI arguments, runs synchronously)
agdt-test-pattern tests/test_state.py::TestSetValue

# Test a specific source file with 100% coverage requirement
agdt-test-file --source-file agentic_devtools/state.py  # Auto-saved for future runs
agdt-task-wait                                          # Wait for completion (REQUIRED!)
```

**WHY background tasks?** The test suite has 2000+ tests and takes ~55 seconds.
Running synchronously causes AI agents to think something went wrong during the
wait, leading to multiple restarts and wasted resources.

## 13. Pre-commit Hooks

The repository has pre-commit hooks for linting Python files in `scripts/`. To enable:

```bash
git config core.hooksPath .githooks
```

The hooks run automatically on `git commit` and check:

- **ruff check**: Lints for pycodestyle errors (E), Pyflakes (F - unused imports/variables), warnings (W), import sorting (I), and pyupgrade (UP)
- **ruff format**: Auto-formats code
- **cspell**: Checks spelling against the dictionary in `cspell.json`

To disable hooks:

```bash
git config --unset core.hooksPath
```

To run checks manually:

```bash
# Ruff lint (with auto-fix)
ruff check --fix --config scripts/agentic_devtools/pyproject.toml scripts/agentic_devtools/

# Ruff format
ruff format --config scripts/agentic_devtools/pyproject.toml scripts/agentic_devtools/

# cspell (use global install, not npx)
cspell lint "scripts/**/*.py"
```

### cspell Dictionary Setup

The `cspell.json` file is the single source of truth for spelling. The VS Code workspace imports it via `cSpell.import`.

**Required global installs** (one-time setup, requires disconnecting from VPN):

```bash
npm install -g cspell @cspell/dict-de-de @cspell/dict-python @cspell/dict-dotnet @cspell/dict-companies @cspell/dict-fullstack @cspell/dict-typescript
```

To add new words, edit `cspell.json` directly (keep alphabetically sorted). Multiple language dictionaries are enabled via imports in `cspell.json`.

## 14. Common Workflows

> **Note:** All action commands (those that mutate state or make API calls) spawn background tasks.
> These return immediately. Use `agdt-task-status` or `agdt-task-wait` to monitor.

### Initial Git Commit & Publish

```bash
# Option A: With CLI parameter (explicit)
agdt-git-save-work --commit-message "feature([DFLY-1234](https://jira.swica.ch/browse/DFLY-1234)): implement feature

- Added new component
- Updated tests

[DFLY-1234](https://jira.swica.ch/browse/DFLY-1234)"
# Returns task ID immediately - use agdt-task-wait to block until complete

# Option B: Parameterless (uses current state)
# Current commit_message: run `agdt-get commit_message` to check
agdt-git-save-work
```

### Amend Commit (Single Commit Policy - Automatic Detection)

`agdt-git-save-work` now automatically detects when to amend instead of creating a new commit:

- If current branch has commits ahead of main AND the last commit contains the same issue key → amend
- Otherwise → new commit

```bash
# Option A: With CLI parameter (explicit)
agdt-git-save-work --commit-message "feature([DFLY-1234](https://jira.swica.ch/browse/DFLY-1234)): implement feature

- Added new component
- Updated tests
- Addressed PR feedback

[DFLY-1234](https://jira.swica.ch/browse/DFLY-1234)"
# Automatically amends if already pushed a commit for this issue

# Option B: Parameterless (uses current state)
# Current commit_message: run `agdt-get commit_message` to check
agdt-git-save-work
```

### Create a Pull Request

```bash
agdt-set source_branch feature/DFLY-1234/my-changes
agdt-set title "feature([DFLY-1234](https://jira.swica.ch/browse/DFLY-1234)): Add new feature"
agdt-set description "This PR implements the new feature."
agdt-create-pull-request
```

### Create a Draft PR (default)

```bash
agdt-set source_branch feature/my-branch
agdt-set title "My PR Title"
agdt-create-pull-request
# Note: PRs are created as drafts by default
```

### Create a Non-Draft PR

```bash
agdt-set source_branch feature/my-branch
agdt-set title "My PR Title"
agdt-set draft false
agdt-create-pull-request
```

### Reply to PR Thread

```bash
agdt-set pull_request_id 23046
agdt-set thread_id 139474
agdt-set content "Thanks for the feedback!

I've addressed your concerns."
agdt-reply-to-pull-request-thread
```

### Reply and Resolve Thread

```bash
agdt-set pull_request_id 23046
agdt-set thread_id 139474
agdt-set resolve_thread true
agdt-set content "Fixed, resolving thread."
agdt-reply-to-pull-request-thread
```

### Add a PR Comment

```bash
agdt-set pull_request_id 23046
agdt-set content "Here's a general comment on this PR."
agdt-add-pull-request-comment
```

### Add a PR Comment with Approval Sentinel

```bash
agdt-set pull_request_id 23046
agdt-set content "LGTM! All acceptance criteria met."
agdt-set is_pr_approval true
agdt-add-pull-request-comment
```

### Approve a Pull Request (Convenience Command)

```bash
agdt-set pull_request_id 23046
agdt-set content "LGTM! Great work on this feature."
agdt-approve-pull-request
# Note: This automatically adds the approval sentinel banner
```

### Resolve a Thread

```bash
agdt-set pull_request_id 23046
agdt-set thread_id 139474
agdt-resolve-thread
```

### Get All PR Threads (Sync - Immediate Output)

```bash
agdt-set pull_request_id 23046
agdt-get-pull-request-threads
```

### Dry Run Mode

```bash
agdt-set dry_run true
agdt-git-save-work  # Previews without executing git commands
agdt-reply-to-pull-request-thread  # Previews without API calls
```

### Pull Request Review Workflow

The `agdt-review-pull-request` command orchestrates the entire PR review process:

```bash
# Option 1: Start with Jira issue key
agdt-set jira.issue_key DFLY-1840
agdt-review-pull-request

# Option 2: Start with PR ID
agdt-set pull_request_id 23523
agdt-review-pull-request

# Option 3: Pass parameters directly
agdt-review-pull-request --pull-request-id 23523 --jira-issue-key DFLY-1840

# Option 4: Include already-reviewed files
agdt-review-pull-request --include-reviewed
```

The command:

1. **Resolves both PR ID and Jira issue key** from params, state, or derived sources:
   - If Jira key provided but no PR ID → searches Jira for linked PRs
   - If PR ID provided but no Jira key → extracts issue key from PR title
2. **Fetches full PR details** (diff, threads, iterations)
3. **Fetches Jira issue details** (if available)
4. **Generates per-file review prompts** in `scripts/temp/pull-request-review/prompts/<pr_id>/`
5. **Prints instructions** for the review workflow

#### Generated Review Artifacts

| File | Purpose |
|------|---------|
| `queue.json` | Review queue manifest (pending/completed files) |
| `pull-request-files.json` | Snapshot of all PR files |
| `pull-request-threads.json` | Snapshot of existing comment threads |
| `pull-request-jira-issue.json` | Copy of linked Jira issue |
| `file-<hash>.md` | Individual file review prompt with diff and threads |

#### File Review Commands

After starting a review, use these commands for each file:

```bash
# Approve a file (no issues found)
agdt-set pull_request_id 23523
agdt-set file_review.file_path "/path/to/file.ts"
agdt-set content "LGTM - code follows conventions"
agdt-approve-file

# Request changes (with line number)
agdt-set line 42
agdt-set content "Consider using a more descriptive variable name"
agdt-request-changes

# Request changes with code suggestion
agdt-set line 42
agdt-set content "```suggestion
const descriptiveVariableName = value;
```"
agdt-request-changes-with-suggestion
```

### Get Jira Issue Details

```bash
agdt-set jira.issue_key DFLY-1234
agdt-get-jira-issue
```

This fetches the issue and:

- Prints formatted details (key, summary, type, labels, description, comments)
- Saves full JSON response to `scripts/temp/temp-get-issue-details-response.json`
- Stores issue in state as `jira.last_issue`

### Add Comment to Jira Issue

```bash
agdt-set jira.issue_key DFLY-1234
agdt-set jira.comment "h4. Progress Update

*Completed:*
* Task 1
* Task 2

*Next Steps:*
* Task 3"
agdt-add-jira-comment
```

After posting, the command automatically refreshes issue details.

### Create Jira Epic

```bash
agdt-set jira.project_key DFLY
agdt-set jira.summary "My Epic Title"
agdt-set jira.epic_name "My Epic Name"
agdt-set jira.role "developer"
agdt-set jira.desired_outcome "a new feature"
agdt-set jira.benefit "improved productivity"
agdt-create-epic
```

### Create Jira Issue

```bash
agdt-set jira.project_key DFLY
agdt-set jira.summary "Bug: Something is broken"
agdt-set jira.description "Detailed description here"
agdt-create-issue
```

Or use the user story format:

```bash
agdt-set jira.project_key DFLY
agdt-set jira.summary "Feature request"
agdt-set jira.role "user"
agdt-set jira.desired_outcome "new capability"
agdt-set jira.benefit "better experience"
agdt-create-issue
```

### Create Subtask

```bash
agdt-set jira.parent_key DFLY-1234
agdt-set jira.summary "Subtask title"
agdt-set jira.description "Subtask details"
agdt-create-subtask
```

### Jira Dry Run Mode

```bash
agdt-set jira.dry_run true
agdt-add-jira-comment  # Previews without posting
```

## 15. Output Files

| File | Command | Content |
|------|---------|---------|
| `scripts/temp/agdt-state.json` | All commands | Persistent state storage |
| `scripts/temp/temp-get-issue-details-response.json` | `agdt-get-jira-issue` | Full Jira API response |
| `scripts/temp/temp-get-pull-request-details-response.json` | `agdt-get-pull-request-details` | Full PR details payload |
| `scripts/temp/pull-request-review/prompts/<pr_id>/` | `agdt-review-pull-request` | Review prompts directory |
| `scripts/temp/temp-<workflow>-<step>-prompt.md` | Workflow initiation commands | Rendered workflow prompts |

### Background Task Storage Structure

Background tasks use a separate storage structure in `scripts/temp/background-tasks/`:

```text
scripts/temp/
├── agdt-state.json                    # Main state file (contains background.recentTasks)
└── background-tasks/
    ├── all-background-tasks.json      # Complete history of all tasks (never pruned)
    └── logs/
        └── <command>_<timestamp>.log  # Task output logs
```

**State Structure:**

The `agdt-state.json` file contains recent tasks under `background.recentTasks`:

```json
{
  "background": {
    "recentTasks": [
      {
        "id": "task-abc123",
        "command": "agdt-git-save-work",
        "status": "completed",
        "start_time": "2024-12-19T15:50:26Z",
        "end_time": "2024-12-19T15:50:28Z",
        "exit_code": 0,
        "log_file": "/path/to/logs/dfly_git_commit_20241219_155026.log"
      }
    ],
    "task_id": "task-abc123"
  }
}
```

**Sorting Rules:**

- Unfinished tasks appear first, sorted by start time (earliest first)
- Finished tasks appear after, sorted by end time (earliest first)

**Auto-Pruning:**

- Recent tasks are automatically pruned when not running and finished more than 5 minutes ago
- The `all-background-tasks.json` file keeps the complete history without pruning

## 16. Instruction Maintenance

Update this file when:

- Adding new CLI commands
- Changing state file structure
- Modifying the auto-approval pattern
- Adding new integrations
- Adding new workflow commands or prompt templates
- Discovering new anti-patterns that AI agents should be warned about
