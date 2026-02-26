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

```
/agdt.work-on-jira-issue.initiate   →  .github/agents/agdt.work-on-jira-issue.initiate.agent.md
/speckit.specify                    →  .github/agents/speckit.specify.agent.md
```

When you invoke a slash command:

1. VS Code loads the agent's instructions from `.github/agents/`
2. The agent executes its steps (calling `agdt-*` CLI commands, reading files, etc.)
3. At the end of each step, **handoff buttons** appear — click one to continue
   to the next step, or type the next slash command manually

You can pass arguments after the command name:

```
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

```
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

**Usage:** Start with `/agdt.work-on-jira-issue.initiate DFLY-1234`, then follow
the handoff buttons to advance through steps. You can also jump to any step
directly if needed.

---

### Pull Request Review (5 steps)

| Step | Command | Description |
|------|---------|-------------|
| 1 | `/agdt.pull-request-review.initiate` | Start a pull request review |
| 2 | `/agdt.pull-request-review.file-review` | Review individual files |
| 3 | `/agdt.pull-request-review.summary` | Generate review summary |
| 4 | `/agdt.pull-request-review.decision` | Approve or request changes |
| 5 | `/agdt.pull-request-review.completion` | Finalize review |

---

### Jira Management (single-step)

| Command | Description |
|---------|-------------|
| `/agdt.create-jira-issue.initiate` | Create a new Jira issue |
| `/agdt.create-jira-epic.initiate` | Create a new Jira epic |
| `/agdt.create-jira-subtask.initiate` | Create a Jira subtask |
| `/agdt.update-jira-issue.initiate` | Update an existing Jira issue |
| `/agdt.apply-pr-suggestions.initiate` | Apply PR review suggestions |

---

### Other Agents

| Command | Description |
|---------|-------------|
| `/security-scan` | Scan code for vulnerabilities and security issues |

---

## Terminal Copilot CLI

When using the **Copilot CLI** (this terminal-based agent), you have two ways
to invoke the same agents:

### Option 1 — Ask naturally (recommended)

Just describe what you want. The agent invokes the appropriate tool:

```
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
`scripts/temp/temp-speckit-<name>-prompt.md`.

> **Note:** The `agdt-speckit-*` shell commands are designed for the terminal
> Copilot CLI. In VS Code Copilot Chat, use `/speckit.*` slash commands instead.

---

## Context Comparison

```
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

See [CONTRIBUTING.md](../CONTRIBUTING.md) for full details.
