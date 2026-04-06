# Workflow Prompt Files

All `agdt-initiate-*-workflow` commands are driven by prompt files that are the
**source of truth for Copilot instructions** — the per-step content and guidance given to
the AI agent for each workflow. Workflow execution logic (preflight checks, background
tasks, status transitions) is implemented in Python and is not covered by these files.
When a workflow is initiated, the CLI renders the appropriate prompt template (saving it to
the workflow state directory), then starts a Copilot CLI session with a short
workflow-specific **bootstrap prompt**. For most workflows, the bootstrap prompt instructs the agent to run
`agdt-get-next-workflow-prompt`, which loads and displays the full rendered prompt. The PR
review workflow is an exception: its bootstrap prompt instructs
`agdt-advance-workflow pull-request-overview` instead.

---

## Source of Truth

The canonical versions of all workflow prompt files are attached to
**[issue #867 — Unify workflow launch](https://github.com/ayaiayorg/agentic-devtools/issues/867#issuecomment-4055694012)**.
That comment is the authoritative reference. If there is any discrepancy between the
template files in `agentic_devtools/prompts/` and the attachments on that comment, the
attachments take precedence.

---

## Prompt File Inventory

The table below lists the canonical prompt file names as attached to the
[#867 source-of-truth comment](https://github.com/ayaiayorg/agentic-devtools/issues/867#issuecomment-4055694012).
This table covers only the subset of workflows tracked there. The full set of in-repo
workflow templates (including `work-on-jira-issue`, `create-jira-epic`, and
`create-jira-subtask`) is shown in the [In-Repo Template Index](#in-repo-template-index)
below. The canonical attachments are the authoritative reference; the in-repo templates
are the editable source.

| Canonical Attachment Name | Workflow | CLI Command |
|---------------------------|----------|-------------|
| `pull-request-review.prompt.md` | PR review workflow | `agdt-initiate-pull-request-review-workflow` |
| `apply-pr-suggestions.prompt.md` | Apply PR review suggestions | `agdt-initiate-apply-pr-suggestions-workflow` |
| `apply-pr-suggestions-command.prompt.md` | Apply PR suggestions (command variant) | `agdt-initiate-apply-pr-suggestions-workflow` |
| `create-issue.prompt.md` | Create Jira issue | `agdt-initiate-create-jira-issue-workflow` |
| `update-issue.prompt.md` | Update Jira issue | `agdt-initiate-update-jira-issue-workflow` |
| `assign-issue.prompt.md` | Assign Jira issue | Manual use (no CLI command yet) |
| `break-down-issue-into-subtasks.prompt.md` | Break down issue into subtasks | Manual use (no CLI command yet) |
| `optimize-issue-for-ai-agent.prompt.md` | Optimize issue for AI agent | Manual use (no CLI command yet) |

Download all files from the
[#867 source-of-truth comment](https://github.com/ayaiayorg/agentic-devtools/issues/867#issuecomment-4055694012).

---

## In-Repo Template Index

All workflow templates live under `agentic_devtools/prompts/<workflow>/default-<step>-prompt.md`.
The table below covers every workflow that has in-repo templates, including those not yet
tracked in the #867 canonical attachments.

| Workflow | In-Repo Template Path(s) | CLI Command |
|----------|--------------------------|-------------|
| PR review | `pull-request-review/default-initiate-prompt.md` (+ 4 step prompts) | `agdt-initiate-pull-request-review-workflow` |
| Apply PR suggestions | `apply-pull-request-review-suggestions/default-initiate-prompt.md` | `agdt-initiate-apply-pr-suggestions-workflow` |
| Create Jira issue | `create-jira-issue/default-initiate-prompt.md` | `agdt-initiate-create-jira-issue-workflow` |
| Update Jira issue | `update-jira-issue/default-initiate-prompt.md` | `agdt-initiate-update-jira-issue-workflow` |
| Create Jira epic | `create-jira-epic/default-initiate-prompt.md` | `agdt-initiate-create-jira-epic-workflow` |
| Create Jira subtask | `create-jira-subtask/default-initiate-prompt.md` | `agdt-initiate-create-jira-subtask-workflow` |
| Work on Jira issue | `work-on-jira-issue/default-<step>-prompt.md` (11 steps) | `agdt-initiate-work-on-jira-issue-workflow` |
| PR merge orchestrator | `pr-merge-orchestrator/default-init-prompt.md` | `agdt-initiate-pr-merge-orchestrator-workflow` |

---

## Prompt File Lifecycle

Each time an `agdt-initiate-*-workflow` command runs, it follows this lifecycle:

```text
Template file
  agentic_devtools/prompts/<workflow>/default-<step>-prompt.md
        │
        │  Variable interpolation
        │  (Jinja2 via agentic_devtools/prompts/loader.py)
        │  Variables supplied from workflow state ({{ variable_name }} syntax)
        ▼
Rendered prompt file saved to disk
  <state-dir>/temp-<workflow>-<step>-prompt.md
        │
        │  Copilot session started with a short static bootstrap prompt
        │  (_start_copilot_session_for_workflow in worktree_setup.py)
        │  Most workflows: "Execute: agdt-get-next-workflow-prompt"
        │  PR review workflow: "Execute: agdt-advance-workflow pull-request-overview"
        ▼
Copilot CLI session
  Bootstrap prompt instructs the agent to run the first workflow command
        │
        ▼
Rendered prompt displayed
  agdt-get-next-workflow-prompt (or agdt-advance-workflow) reads the
  rendered temp file and prints the full workflow instructions to the agent
```

Two session modes are possible depending on context:

- **VS Code auto-start** (`folderOpen` task): injected before VS Code opens, always
  starts an interactive Copilot session in the integrated terminal, regardless of the
  `--interactive` flag.
- **Direct invocation**: controlled by `--interactive` (default: `false`). With
  `--interactive false` Copilot runs as a detached background process (no agdt task ID;
  check the Copilot session log file via the `copilot.*` state keys); with
  `--interactive true` it attaches to the terminal (requires a TTY and VS Code to be
  available).

Override templates are supported: place an
`agentic_devtools/prompts/<workflow>/override-<step>-prompt.md` file to replace the
default without modifying the package source. Override templates cannot introduce new
variables that are absent from the default.

---

## How to Update Prompt Files

### For template changes (in-repo)

1. Edit the template file in `agentic_devtools/prompts/<workflow>/default-<step>-prompt.md`.
2. Variables use `{{ variable_name }}` syntax (Jinja2). The variable names must match the
   keys available in workflow state at the time the step runs (dot notation is converted to
   underscores, e.g. `jira.issue_key` → `{{ jira_issue_key }}`).
3. Run `agdt-test` and verify the full test suite still passes.
4. Upload the updated file as a new attachment on the
   [#867 source-of-truth comment](https://github.com/ayaiayorg/agentic-devtools/issues/867#issuecomment-4055694012)
   so the canonical attachment stays in sync.

### For custom overrides (per-repo)

Place an override file alongside the default:

```text
agentic_devtools/prompts/<workflow>/override-<step>-prompt.md
```

The override file is loaded instead of the default and must not introduce variables that
the default does not already declare.

---

## Manual / Legacy Fallback

If the automated Copilot session cannot be launched (for example, `gh copilot` is not
installed, there is no TTY, or VS Code is unavailable), the workflow degrades gracefully:

1. The rendered prompt is **printed to the console**.
2. The rendered prompt is **saved** to `temp-<workflow>-<step>-prompt.md` in the workflow
   state directory (`.agdt/workflows/…/`).
3. A notice is printed indicating where the file was saved.

You can then paste the prompt manually into GitHub Copilot Chat or any other AI assistant.

By default (`--interactive` omitted or `--interactive false`), the Copilot session runs
as a detached background process (no agdt task ID). To monitor it, check the Copilot
session log file via the `copilot.*` state keys. To request an interactive terminal
session, pass `--interactive true` (requires a TTY and VS Code):

```bash
agdt-initiate-pull-request-review-workflow --pull-request-id 12345 --interactive true
```

### Copilot Model Selection

All `agdt-initiate-*-workflow` commands accept a `--model` flag to select which Copilot
model to use for the session.  The default model is resolved in this order:

1. The `--model` CLI flag (highest priority)
2. `default_copilot_model` in `.agdt/config/project.json` (set by `agdt-setup`)
3. Hardcoded fallback `gpt-4o`

Run `agdt-setup` to interactively select and persist your preferred default model.

```bash
# Use the configured default model
agdt-initiate-pull-request-review-workflow --pull-request-id 12345

# Override with a specific model
agdt-initiate-pull-request-review-workflow --pull-request-id 12345 --model gpt-5.3-codex
agdt-initiate-work-on-jira-issue-workflow --issue-key PROJECT-1234 --model claude-opus-4.6
```

The selected model is:

- Passed to the Copilot CLI via `--model <model_id>` (standalone binary only; the
  `gh copilot suggest` fallback does not support this flag — a warning is emitted).
- Persisted in workflow state as `copilot.model_id` for traceability.
- Printed to stdout at session start (e.g. `Copilot model: gpt-5.3-codex`).
- Forwarded through the auto-setup worktree re-invocation path so the same model is
  used after automatic environment setup.

For CI pipelines and other headless environments, omit `--interactive` (or pass
`--interactive false`) to run the session non-interactively.
