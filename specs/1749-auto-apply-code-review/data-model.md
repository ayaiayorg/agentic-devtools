# Data Model: Auto-apply Code Review Suggestions

## Entities

### ExclusionContext (new)

- Purpose: carry resolved review comment IDs from apply step to repair dispatch step.
- Core fields:
  - `resolved_comment_ids: set[int]` (REST `databaseId` values from `PullRequestReviewComment`)

### ApplySuggestionsResult (new)

- Purpose: structured output for batch and bisection apply flows.
- Core fields:
  - `applied_ids: list[str]` (GraphQL `PullRequestReviewComment.id` values for suggestions that were applied)
  - `skipped_ids: list[str]` (GraphQL `PullRequestReviewComment.id` values for suggestions that were skipped)
  - `commit_shas: list[str]`
  - `error: str | None`

## Invariants

1. Excluded review comments are never re-dispatched for repair in the same loop run.
2. `ApplySuggestionsResult` tracks suggestion IDs, while dispatch exclusion tracks parent review comment REST IDs.
3. Retry behavior follows shared `retry_with_backoff` defaults unless explicitly overridden.
