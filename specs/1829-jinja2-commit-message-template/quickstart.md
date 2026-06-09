# Quickstart: Jinja2 Commit Message Template

1. Run `agdt-setup` in your repository without `--skip-templates`, and only in
   a mode that allows repo file creation.
2. Confirm `.agdt/config/commit-template.j2` exists. If it does not, rerun
   setup without `--skip-templates` (or with repo steps enabled) before relying
   on template rendering.
3. Customize the template if needed.
4. Set relevant state keys (`versionControl.commitMessage*`, plus `issue_key` or
   `jira.issue_key`). `issueManagement.issueLink` is optional for explicit
   overrides, but required when using Jira-style keys (for GitHub numeric /
   `#N` keys it can be auto-derived when repo resolution succeeds).
5. Run `agdt-git-save-work`.

Commit message priority order:

1. `--commit-message` CLI argument
2. Rendered template from `.agdt/config/commit-template.j2`
3. Existing `commit_message` state fallback

If template rendering fails, the command falls back to state-based commit message resolution with warnings.
