# Research: Pull Request Body Template with Commit Aggregation Fallback

## Decision Summary

- Use a shared `resolve_pr_body()` utility so Azure DevOps and GitHub consume identical PR-body resolution behavior.
- Resolve `fullCommitMessage` via strict fallback order: state key `git.last_commit_message` → git log aggregation → literal fallback.
- Parse git log output with an explicit record delimiter (`%x1e`) to split multi-commit output safely.
- Keep `.agdt/config/pull-request-template.md` user-managed after initialization; never overwrite user customizations.

## Rationale

- A shared utility enforces cross-platform consistency required by the spec and avoids duplicated fallback logic.
- Delimiter-based parsing avoids ambiguous commit-boundary detection when commit bodies are multi-line.
- User ownership of the template preserves team-specific checklists while still enabling automated interpolation.
