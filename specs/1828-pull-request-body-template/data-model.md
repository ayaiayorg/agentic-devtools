# Data Model: PR Body Template Resolution

## Entity: `PRTemplateConfig`

- `template_path: Path` — resolved location for `.agdt/config/pull-request-template.md`
- `template_exists: bool` — whether template file is present
- `template_is_empty: bool` — whether template content is whitespace-only

## Entity: `CommitMessageResolution`

- `state_message: str | None` — cached `git.last_commit_message`
- `git_log_messages: list[str]` — parsed commit messages from `git log --format=%B%x1e {ref}..HEAD`
- `resolved_full_commit_message: str` — final value used for interpolation/fallback
- `source: Literal["state", "git_log", "literal_fallback"]`

## Entity: `PRBodyResolution`

- `template_content: str | None` — raw template file content when present
- `placeholder_present: bool` — whether `{{fullCommitMessage}}` appears in template content
- `resolved_body: str` — final PR body passed to platform command (`az repos pr create` or `gh pr create`)

## Notes

- `commit_message` remains the input key for commit authoring workflows.
- `git.last_commit_message` is a distinct output key persisted after successful commit/amend operations.
