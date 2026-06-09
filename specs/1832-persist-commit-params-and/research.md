# Research: Persist Commit Params and Rendered Messages to State

## Scope

This research captures implementation decisions for persisting commit-derived metadata in workflow state for issue #1832.

## Decisions

1. **Atomic state writes**
   - Use `read_modify_write_state()` for a single locked read/modify/write transaction.
   - Rationale: prevents partial key updates when multiple background tasks may write state.

2. **Fallback placement**
   - Implement `git.last_commit_message` fallback in `commit_cmd()` before calling `get_commit_message()`.
   - Rationale: keeps `get_commit_message()` in `core.py` as a focused reader of `commit_message`.

3. **Title/body extraction**
   - Derive title from the first line (split on first newline).
   - Persist body as the remaining content with one leading blank separator removed.

4. **Persistence ordering**
   - Persist metadata immediately after successful commit/amend and before push/rebase/sync steps.
   - Rationale: commit may exist locally even if subsequent network operations fail.

## Referenced Artifacts

- Specification: [spec.md](./spec.md)
- Implementation plan: [plan.md](./plan.md)
