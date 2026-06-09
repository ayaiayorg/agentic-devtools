# Data Model: Jinja2 Commit Message Template

## Template File

- Path: `.agdt/config/commit-template.j2`
- Scope: repository-local, versionable text file
- Format: Jinja2 template

## Render Variables

- `issueType`: conventional commit type resolved from
  `versionControl.commitMessageType`, with fallback mapping from
  `issueManagement.issueType` or `jira.issue_type` using FR-003 defaults
  unless overridden by configuration
- `issueKey`: issue key resolved from `issue_key`, then `jira.issue_key`, with optional future alias support for `issueManagement.issueKey`
- `issueLink`: `issueManagement.issueLink` (explicit override) → derived `https://github.com/{owner_repo}/issues/{N}` when `issueKey` is GitHub-numeric/`#N` and repo resolves → unresolved
- `commitMessageTitle`: `versionControl.commitMessageTitle`
- `commitMessageBody`: content read from the file path in `versionControl.commitMessageBodyFile` (absolute, or relative to git repository root)

## Resolution Semantics

- Variables that cannot be resolved are omitted from the render context.
- Jinja2 `SilentUndefined` renders omitted variables as empty strings.
- Referenced-but-unresolved variables emit warnings.
