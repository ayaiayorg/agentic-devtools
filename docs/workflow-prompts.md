# Workflow Prompt Files

All `agdt-initiate-*-workflow` commands are driven by prompt files that serve as the
**sole source of truth** for workflow automation in agentic-devtools. When a workflow is
initiated, the CLI loads the appropriate prompt template, interpolates runtime variables,
and feeds the rendered prompt directly to a Copilot CLI session in the VS Code integrated
terminal.

---

## Source of Truth

The canonical versions of all workflow prompt files are attached to
**[issue #867 — Unify workflow launch](https://github.com/ayaiayorg/agentic-devtools/issues/867#issuecomment-4055694012)**.
That comment is the authoritative reference. If there is any discrepancy between the
template files in `agentic_devtools/prompts/` and the attachments on that comment, the
attachments take precedence.

---

## Prompt File Inventory

| File Name | Workflow | CLI Command |
|-----------|----------|-------------|
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
Rendered prompt file
  <state-dir>/temp-<workflow>-<step>-prompt.md
        │
        │  Automatic Copilot session launch
        │  (_start_copilot_session_for_workflow in worktree_setup.py)
        ▼
Copilot CLI session
  VS Code integrated terminal (interactive) or background task (non-interactive)
```

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

To explicitly opt out of interactive session launch, pass `--interactive false`:

```bash
agdt-initiate-pull-request-review-workflow --pull-request-id 12345 --interactive false
```

This is the recommended mode for CI pipelines and headless environments.
