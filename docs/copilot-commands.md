# Copilot Commands Reference

This document covers all AI agent commands available in **agentic-devtools**,
how to invoke them, and when to use each context.

---

## Two Contexts, One Set of Agents

The same agents work in two different environments:

| Context | How to invoke | Best for |
|---------|--------------|----------|
| **VS Code Copilot Chat** | `/agdt.workflow.step` or `/speckit.command` | Starting and stepping through multi-turn workflows interactively |
| **Terminal Copilot CLI** | Ask the agent naturally, or run `agdt-speckit-*` shell commands | Running single commands, scripting, CI pipelines |

---

## VS Code Copilot Chat

### How slash commands work

Type `/` in the Copilot Chat input field and VS Code will show all available
agents. Each agent maps directly to a file in `.github/agents/`:

```text
/agdt.work-on-jira-issue.initiate   →  .github/agents/agdt.work-on-jira-issue.initiate.agent.md
/speckit.specify                    →  .github/agents/speckit.specify.agent.md
```

When you invoke a slash command:

1. VS Code loads the agent's instructions from `.github/agents/`
2. The agent executes its steps (calling `agdt-*` CLI commands, reading files, etc.)
3. At the end of each step, **handoff buttons** appear — click one to continue
   to the next step, or type the next slash command manually

You can pass arguments after the command name:

```text
/speckit.specify I want to add OAuth2 login for enterprise users
```

---

## Spec-Driven Development (SpecKit) Commands

Use these to build features using the Specification-Driven Development (SDD)
workflow. Run them in order for a new feature.

| Command | Description |
|---------|-------------|
| `/speckit.specify <feature description>` | Create or update a feature spec from a natural language description. **Start here.** |
| `/speckit.clarify` | Ask up to 5 targeted clarification questions and encode the answers back into the spec |
| `/speckit.plan` | Generate a technical implementation plan from the spec |
| `/speckit.checklist` | Generate a custom quality checklist for the feature |
| `/speckit.tasks` | Generate an actionable, dependency-ordered `tasks.md` from the plan |
| `/speckit.analyze` | Cross-artifact consistency check across `spec.md`, `plan.md`, and `tasks.md` — run before implementing |
| `/speckit.implement` | Execute all tasks in `tasks.md` in order |
| `/speckit.taskstoissues` | Convert `tasks.md` into GitHub issues |
| `/speckit.constitution` | Create or update the project constitution (guiding principles) |

### Typical SDD flow

```text
/speckit.specify Add a dark mode toggle to the settings page
        ↓
/speckit.clarify          (optional — resolve ambiguities)
        ↓
/speckit.plan
        ↓
/speckit.checklist        (optional — custom quality gates)
        ↓
/speckit.tasks
        ↓
/speckit.analyze          (catch issues before coding)
        ↓
/speckit.implement
```

---

## AGDT Workflow Commands

All `agdt-initiate-*-workflow` commands automatically launch a Copilot CLI session after
workflow initiation (and auto-setup when needed). The rendered prompt is saved to the
workflow state directory; the session starts with a short workflow-specific **bootstrap
prompt**. For most workflows the bootstrap prompt instructs the agent to run
`agdt-get-next-workflow-prompt`, which loads the full rendered prompt. For the PR review
workflow the bootstrap prompt instructs `agdt-advance-workflow pull-request-overview`
instead. Prompt files are documented in [Workflow Prompt Files](workflow-prompts.md).

When a new worktree is opened in VS Code, a `folderOpen` auto-start task starts an
interactive Copilot session in the integrated terminal regardless of `--interactive`. For
direct CLI invocations, omit `--interactive` (or pass `--interactive false`) to run the
Copilot session as a detached background process (not an agdt background task — no task
ID; use the `copilot.*` state keys to locate the session log file), or pass
`--interactive true` to attach to an interactive terminal (requires a TTY and VS Code). If
the session cannot be launched, the rendered prompt is printed to the console as a
fallback.

### Work on Jira Issue (11 steps)

Full end-to-end workflow for implementing a Jira issue.

| Step | Command | Description |
|------|---------|-------------|
| 1 | `/agdt.work-on-jira-issue.initiate` | Start working on a Jira issue |
| 2 | `/agdt.work-on-jira-issue.setup` | Create worktree and branch |
| 3 | `/agdt.work-on-jira-issue.retrieve` | Fetch Jira issue details |
| 4 | `/agdt.work-on-jira-issue.planning` | Analyze issue and post plan |
| 5 | `/agdt.work-on-jira-issue.checklist-creation` | Create implementation checklist |
| 6 | `/agdt.work-on-jira-issue.implementation` | Implement checklist items |
| 7 | `/agdt.work-on-jira-issue.implementation-review` | Review completed checklist |
| 8 | `/agdt.work-on-jira-issue.verification` | Run tests and quality gates |
| 9 | `/agdt.work-on-jira-issue.commit` | Stage and commit changes |
| 10 | `/agdt.work-on-jira-issue.pull-request` | Create a pull request |
| 11 | `/agdt.work-on-jira-issue.completion` | Post final Jira comment |

**Usage:** Start with `/agdt.work-on-jira-issue.initiate PROJECT-1234`, then follow
the handoff buttons to advance through steps. You can also jump to any step
directly if needed.

---

### Pull Request Review (5 steps)

| Step | Command | Description |
|------|---------|-------------|
| 1 | `/agdt.pull-request-review.initiate` | Start a pull request review |
| 2 | CLI: `agdt-advance-workflow pull-request-overview` | Display PR details and review criteria |
| 3 | `/agdt.pull-request-review.file-review` | Review individual files |
| 4 | `/agdt.pull-request-review.decision` | Approve or request changes |
| 5 | `/agdt.pull-request-review.completion` | Finalize review |

> **Note:** Step 2 is a CLI command, not a Copilot Chat agent step.

---

### Jira Management (single-step)

| Command | Description |
|---------|-------------|
| `/agdt.create-jira-issue.initiate` | Create a new Jira issue |
| `/agdt.create-jira-epic.initiate` | Create a new Jira epic |
| `/agdt.create-jira-subtask.initiate` | Create a Jira subtask |
| `/agdt.update-jira-issue.initiate` | Update an existing Jira issue |
| `/agdt.apply-pr-suggestions.initiate` | Apply PR review suggestions |
| `/agdt.optimize-issue-for-ai-agent.initiate` | Optimize a Jira issue for AI agent consumption |
| `/agdt.break-down-issue-into-subtasks.initiate` | Break down a Jira issue into subtasks |

> **Note:** Most `initiate` commands above auto-launch a Copilot session with a workflow-specific
> bootstrap prompt. Current exceptions are `agdt-initiate-optimize-issue-for-ai-agent-workflow`
> and `agdt-initiate-break-down-issue-into-subtasks-workflow`, which currently initialize
> workflow state but do not start a session yet. For Jira / apply-suggestions workflows that
> do auto-launch, the first command is
> `agdt-get-next-workflow-prompt`; for PR review it is
> `agdt-advance-workflow pull-request-overview`. Pass `--interactive true` for an interactive
> terminal session (TTY + VS Code required); omit the flag for non-interactive execution
> (default, runs as a detached background process — not an agdt background task, so
> `agdt-task-*` commands do not apply; use `copilot.*` state keys to find the log file).
> When a new worktree is opened in VS Code, a `folderOpen` task starts an interactive session
> automatically regardless of `--interactive`. See
> [Workflow Prompt Files](workflow-prompts.md) for prompt file details.

---

### Standalone Utility Prompts

These prompts cover common git tasks. Each has both an `.agent.md` file in
`.github/agents/` and a detailed `.prompt.md` file in `.github/prompts/`.
The agent delegates to the prompt for full instructions.

| Command | Description |
|---------|-------------|
| `/agdt.address-copilot-review` | Address GitHub Copilot PR review comments end-to-end by review URL |
| `/agdt.squash-commits` | Squash multiple commits on a feature branch into a single well-formed commit |
| `/agdt.resolve-merge-conflicts` | Resolve merge conflicts systematically with file-type-specific strategies |

---

### Other Agents

| Command | Description |
|---------|-------------|
| `/security-scan` | Scan code for vulnerabilities and security issues |

---

### Individual CLI Command Agents

Every `agdt-*` CLI command has a corresponding agent in `.github/agents/` and a
prompt stub in `.github/prompts/`. Most of these wrappers are invoked from
VS Code Copilot Chat via `/agdt.<command-name>`, while `agdt-speckit-*`
commands are exposed via `/speckit.*` (for example, `/speckit.plan`).

#### State Management

| Command | CLI | Description |
|---------|-----|-------------|
| `/agdt.set` | `agdt-set` | Set a key-value pair in the agdt state |
| `/agdt.get` | `agdt-get` | Retrieve a value from the agdt state |
| `/agdt.delete` | `agdt-delete` | Remove a key from the agdt state |
| `/agdt.clear` | `agdt-clear` | Remove all values from the agdt state |
| `/agdt.show` | `agdt-show` | Display all current state values |

#### Workflow State

| Command | CLI | Description |
|---------|-----|-------------|
| `/agdt.get-workflow` | `agdt-get-workflow` | Display current workflow state |
| `/agdt.clear-workflow` | `agdt-clear-workflow` | Clear the current workflow state |

#### Workflow Management

| Command | CLI | Description |
|---------|-----|-------------|
| `/agdt.advance-workflow` | `agdt-advance-workflow` | Advance to next workflow step |
| `/agdt.get-next-workflow-prompt` | `agdt-get-next-workflow-prompt` | Get the next workflow step prompt |
| `/agdt.create-checklist` | `agdt-create-checklist` | Create a workflow checklist |
| `/agdt.update-checklist` | `agdt-update-checklist` | Update checklist items |
| `/agdt.show-checklist` | `agdt-show-checklist` | Display current checklist |
| `/agdt.setup-worktree-background` | `agdt-setup-worktree-background` | Set up a git worktree in the background |

#### Azure DevOps

| Command | CLI | Description |
|---------|-----|-------------|
| `/agdt.add-pull-request-comment` | `agdt-add-pull-request-comment` | Post a comment on a pull request |
| `/agdt.approve-pull-request` | `agdt-approve-pull-request` | Approve a pull request with sentinel banner |
| `/agdt.create-pull-request` | `agdt-create-pull-request` | Create a new pull request |
| `/agdt.get-pull-request-threads` | `agdt-get-pull-request-threads` | Retrieve all comment threads |
| `/agdt.reply-to-pull-request-thread` | `agdt-reply-to-pull-request-thread` | Reply to a comment thread |
| `/agdt.resolve-thread` | `agdt-resolve-thread` | Resolve a PR comment thread |
| `/agdt.mark-pull-request-draft` | `agdt-mark-pull-request-draft` | Mark a pull request as draft |
| `/agdt.publish-pull-request` | `agdt-publish-pull-request` | Publish a draft pull request |
| `/agdt.get-pull-request-details` | `agdt-get-pull-request-details` | Retrieve full pull request details |
| `/agdt.approve-file` | `agdt-approve-file` | Approve a file during PR review |
| `/agdt.request-changes` | `agdt-request-changes` | Request changes on a file |
| `/agdt.request-changes-with-suggestion` | `agdt-request-changes-with-suggestion` | Request changes with code suggestions |
| `/agdt.mark-file-reviewed` | `agdt-mark-file-reviewed` | Mark a file as reviewed |
| `/agdt.confirm-suggestion-addressed` | `agdt-confirm-suggestion-addressed` | Confirm a review suggestion was addressed |
| `/agdt.reject-suggestion-resolution` | `agdt-reject-suggestion-resolution` | Reject a suggestion resolution |
| `/agdt.run-e2e-tests-synapse` | `agdt-run-e2e-tests-synapse` | Trigger Synapse E2E test pipeline |
| `/agdt.run-e2e-tests-fabric` | `agdt-run-e2e-tests-fabric` | Trigger Fabric E2E test pipeline |
| `/agdt.run-wb-patch` | `agdt-run-wb-patch` | Trigger workbench patch pipeline |
| `/agdt.get-run-details` | `agdt-get-run-details` | Retrieve pipeline run details |
| `/agdt.wait-for-run` | `agdt-wait-for-run` | Wait for a pipeline run to complete |
| `/agdt.list-pipelines` | `agdt-list-pipelines` | List Azure DevOps pipelines |
| `/agdt.get-pipeline-id` | `agdt-get-pipeline-id` | Retrieve a pipeline ID by name |
| `/agdt.create-pipeline` | `agdt-create-pipeline` | Create an Azure DevOps pipeline |
| `/agdt.update-pipeline` | `agdt-update-pipeline` | Update an Azure DevOps pipeline |

#### Azure CLI (App Insights)

| Command | CLI | Description |
|---------|-----|-------------|
| `/agdt.query-app-insights` | `agdt-query-app-insights` | Run an Azure App Insights query |
| `/agdt.query-fabric-dap-errors` | `agdt-query-fabric-dap-errors` | Query Fabric DAP error logs |
| `/agdt.query-fabric-dap-provisioning` | `agdt-query-fabric-dap-provisioning` | Query Fabric DAP provisioning logs |
| `/agdt.query-fabric-dap-timeline` | `agdt-query-fabric-dap-timeline` | Query Fabric DAP timeline logs |

#### VPN

| Command | CLI | Description |
|---------|-----|-------------|
| `/agdt.vpn-off` | `agdt-vpn-off` | Disconnect from VPN |
| `/agdt.vpn-on` | `agdt-vpn-on` | Connect to VPN |
| `/agdt.vpn-status` | `agdt-vpn-status` | Check VPN connection status |

#### Jira (Individual Commands)

| Command | CLI | Description |
|---------|-----|-------------|
| `/agdt.create-epic` | `agdt-create-epic` | Create a new Jira epic |
| `/agdt.create-issue` | `agdt-create-issue` | Create a new Jira issue |
| `/agdt.create-subtask` | `agdt-create-subtask` | Create a new Jira subtask |
| `/agdt.add-jira-comment` | `agdt-add-jira-comment` | Add a comment to a Jira issue |
| `/agdt.get-jira-issue` | `agdt-get-jira-issue` | Retrieve Jira issue details |
| `/agdt.update-jira-issue` | `agdt-update-jira-issue` | Update Jira issue fields |
| `/agdt.list-project-roles` | `agdt-list-project-roles` | List Jira project roles |
| `/agdt.get-project-role-details` | `agdt-get-project-role-details` | Get Jira project role details |
| `/agdt.add-users-to-project-role` | `agdt-add-users-to-project-role` | Add users to a Jira project role |
| `/agdt.add-users-to-project-role-batch` | `agdt-add-users-to-project-role-batch` | Batch add users to a role |
| `/agdt.find-role-id-by-name` | `agdt-find-role-id-by-name` | Find a Jira role ID by name |
| `/agdt.check-user-exists` | `agdt-check-user-exists` | Check if a Jira user exists |
| `/agdt.check-users-exist` | `agdt-check-users-exist` | Check if multiple Jira users exist |
| `/agdt.parse-jira-error-report` | `agdt-parse-jira-error-report` | Parse a Jira error report |

#### Git

| Command | CLI | Description |
|---------|-----|-------------|
| `/agdt.git-save-work` | `agdt-git-save-work` | Stage, commit/amend, and push changes |
| `/agdt.git-sync` | `agdt-git-sync` | Sync local branch with remote |
| `/agdt.git-stage` | `agdt-git-stage` | Stage all changes |
| `/agdt.git-push` | `agdt-git-push` | Push to origin |
| `/agdt.git-force-push` | `agdt-git-force-push` | Force push to origin |
| `/agdt.git-publish` | `agdt-git-publish` | Publish branch upstream |

#### Testing

| Command | CLI | Description |
|---------|-----|-------------|
| `/agdt.test` | `agdt-test` | Run full test suite with coverage |
| `/agdt.test-quick` | `agdt-test-quick` | Run tests without coverage |
| `/agdt.test-file` | `agdt-test-file` | Run tests for a specific source file |
| `/agdt.test-pattern` | `agdt-test-pattern` | Run specific tests by pattern |

#### Background Tasks

| Command | CLI | Description |
|---------|-----|-------------|
| `/agdt.tasks` | `agdt-tasks` | List all background tasks |
| `/agdt.task-status` | `agdt-task-status` | Show detailed task status |
| `/agdt.task-log` | `agdt-task-log` | Display task output log |
| `/agdt.task-wait` | `agdt-task-wait` | Wait for task completion |
| `/agdt.tasks-clean` | `agdt-tasks-clean` | Clean up expired tasks |
| `/agdt.show-other-incomplete-tasks` | `agdt-show-other-incomplete-tasks` | Show incomplete background tasks |

#### GitHub Issue Creation

| Command | CLI | Description |
|---------|-----|-------------|
| `/agdt.create-agdt-issue` | `agdt-create-agdt-issue` | Create a GitHub issue in agentic-devtools |
| `/agdt.create-agdt-bug-issue` | `agdt-create-agdt-bug-issue` | Create a bug issue |
| `/agdt.create-agdt-feature-issue` | `agdt-create-agdt-feature-issue` | Create a feature issue |
| `/agdt.create-agdt-documentation-issue` | `agdt-create-agdt-documentation-issue` | Create a documentation issue |
| `/agdt.create-agdt-task-issue` | `agdt-create-agdt-task-issue` | Create a task issue |

#### Setup

| Command | CLI | Description |
|---------|-----|-------------|
| `/agdt.setup` | `agdt-setup` | Run full agentic-devtools setup |
| `/agdt.setup-copilot-cli` | `agdt-setup-copilot-cli` | Set up GitHub Copilot CLI |
| `/agdt.setup-gh-cli` | `agdt-setup-gh-cli` | Set up GitHub CLI |
| `/agdt.setup-check` | `agdt-setup-check` | Verify setup configuration |
| `/agdt.setup-certs` | `agdt-setup-certs` | Set up SSL certificates |

#### Azure Context

| Command | CLI | Description |
|---------|-----|-------------|
| `/agdt.azure-context-use` | `agdt-azure-context-use` | Switch Azure context |
| `/agdt.azure-context-status` | `agdt-azure-context-status` | Show Azure context status |
| `/agdt.azure-context-current` | `agdt-azure-context-current` | Show current Azure context |
| `/agdt.azure-context-ensure-login` | `agdt-azure-context-ensure-login` | Ensure Azure CLI is logged in |

#### Network

| Command | CLI | Description |
|---------|-----|-------------|
| `/agdt.network-status` | `agdt-network-status` | Check network connectivity |
| `/agdt.vpn-run` | `agdt-vpn-run` | Run a command through VPN |

#### Release

| Command | CLI | Description |
|---------|-----|-------------|
| `/agdt.release-pypi` | `agdt-release-pypi` | Publish package to PyPI |

#### Copilot

| Command | CLI | Description |
|---------|-----|-------------|
| `/agdt.copilot-auto-start` | `agdt-copilot-auto-start` | Auto-start a Copilot session |

#### Review

| Command | CLI | Description |
|---------|-----|-------------|
| `/agdt.review` | `agdt-review` | Review command group; use a subcommand (for example `dispatch`, `status`, `config-get`, or `config-validate`) |

---

## Terminal Copilot CLI

When using the **Copilot CLI** (this terminal-based agent), you have two ways
to invoke the same agents:

### Option 1 — Ask naturally (recommended)

Just describe what you want. The agent invokes the appropriate tool:

```text
run speckit analyze
run speckit specify — add OAuth2 login
run the PR review initiate workflow
```

### Option 2 — Shell commands

The `agdt-speckit-*` commands render the agent prompt to stdout. The Copilot
CLI reads the output and executes it:

```bash
agdt-speckit-analyze
agdt-speckit-specify "add OAuth2 login"
agdt-speckit-plan
agdt-speckit-tasks
agdt-speckit-implement
agdt-speckit-clarify
agdt-speckit-checklist
agdt-speckit-constitution
agdt-speckit-taskstoissues
```

Each command prints the full agent prompt and saves it to
`temp-speckit-<name>-prompt.md` in the workflow state directory.

> **Note:** The `agdt-speckit-*` shell commands are designed for the terminal
> Copilot CLI. In VS Code Copilot Chat, use `/speckit.*` slash commands instead.

---

## Context Comparison

```text
┌─────────────────────────────────────────────────────────────────────┐
│  VS Code Copilot Chat                                                │
│                                                                      │
│  /speckit.specify Add dark mode    ← slash command with argument     │
│  [Continue to Plan] [Clarify]      ← handoff buttons appear         │
│  /speckit.plan                     ← next step                      │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  Terminal Copilot CLI (this chat)                                    │
│                                                                      │
│  You: "run speckit specify — add dark mode"                          │
│  Agent: invokes speckit.specify task tool directly                   │
│                                                                      │
│  — OR —                                                              │
│                                                                      │
│  $ agdt-speckit-specify "add dark mode"   ← prints prompt to stdout  │
│  You: "execute that"                      ← agent acts on output     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Adding New Agents

To add a new slash command/agent:

1. Create `.github/agents/<name>.agent.md` with a `description:` frontmatter field
2. Create `.github/prompts/<name>.prompt.md` with an `agent: <name>` frontmatter field
3. For terminal CLI support, add a `agdt-speckit-*` entry in
   `agentic_devtools/cli/speckit/commands.py`, `runner.py`, and `pyproject.toml`
4. For workflow prompt templates, add a default template in
   `agentic_devtools/prompts/<workflow>/default-<step>-prompt.md` and upload the
   canonical version as an attachment on the
   [#867 source-of-truth comment](https://github.com/ayaiayorg/agentic-devtools/issues/867#issuecomment-4055694012).
   See [Workflow Prompt Files](workflow-prompts.md) for the full prompt lifecycle.

See [CONTRIBUTING.md](../CONTRIBUTING.md) for full details.
