# Data Model: Persist Commit Params and Rendered Messages to State

## Persisted State Keys

| Key | Type | Description |
| --- | --- | --- |
| `commit_message_title` | `string` | First line of the last successfully committed message; output metadata for downstream reuse. |
| `git.last_commit_title` | `string` | Audit/debug alias of the last commit title. |
| `git.last_commit_message` | `string` | Full rendered commit message persisted verbatim (title/body/footer). |
| `git.last_commit_body` | `string` | Body portion of the last commit message; empty string for title-only commits. |

## Update Rules

- Keys are updated only after successful non-dry-run commit/amend operations.
- All four keys are written atomically in one locked state update.
- Each successful commit/amend overwrites previous values.
