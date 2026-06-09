# Research: Jinja2 Commit Message Template System

## Decisions

1. Add a dedicated `cli/git/commit_template.py` module instead of coupling to prompt-loading code.
2. Reuse existing `SilentUndefined` behavior for empty-string rendering of missing variables.
3. Add a non-exiting repository resolver for template rendering paths.
4. Use Jinja2 AST/meta parsing for referenced-variable validation and unresolved-variable warnings.

## Rationale

- Keeps commit-message templating isolated and testable.
- Preserves existing `agdt-git-save-work` behavior when templates are absent or invalid.
- Supports flexible Jinja2 expressions without regex-based false negatives.
