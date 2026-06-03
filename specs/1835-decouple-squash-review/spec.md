# Feature Specification: Decouple Squash Step from Copilot Review Triggering

<!-- Source Issue: https://github.com/ayaiayorg/agentic-devtools/issues/1835 -->

## Summary

Decouple the squash pipeline action from Copilot review triggering so that squash
is responsible strictly for commit hygiene and review requests are always routed
explicitly through `RequestReviewAction`.

## Problem Statement

The squash action in the agentic-devtools PR pipeline previously had a side effect:
`squash_post_repair()` in the GitHub provider both squashed commits AND re-requested
Copilot review. With the shift to always requesting reviews explicitly via
agentic-devtools (rather than relying on auto-trigger via push events), this coupling
is obsolete and causes confusion.

The spec from issue #1617 assumed:

> "For PRs with >1 commit, the force-push from a squash naturally triggers a new
> Copilot review via GitHub's push event."

This is no longer true. Reviews are now always explicitly requested via
`RequestReviewAction`.

## Solution

### Changes Made

1. **`squash_post_repair()` in `GitHubActionsProvider`**: Removed the review-requesting
   logic (steps 3 and 3b that called `_request_copilot_review`). The method now only
   performs squash operations and draft-publish safety.

2. **`CIPlatformProvider` ABC**: Updated the `squash_post_repair()` docstring to
   reflect its strict commit-hygiene responsibility.

3. **`SquashAction`**: Updated docstring to clarify it does not trigger reviews and
   that `RequestReviewAction` handles review requests explicitly after squash.

4. **`RequestReviewAction`**: Updated docstring to clarify it is the single, explicit
   mechanism for requesting reviews — never triggered implicitly via push events.

5. **Spec language in `specs/1617-loop-review-request-logic/spec.md`**: Corrected
   references to "force-push naturally triggers review" to reflect the explicit
   review request model.

6. **Unused import removed**: `_request_copilot_review` import removed from
   `github_provider.py` as it is no longer used by `squash_post_repair()`.

### Pipeline Flow (After)

```text
SquashAction (commit hygiene only)
  → invalidates_snapshot=True (HEAD changed)
  → Pipeline runner refreshes snapshot
  → RequestReviewAction (runs_after_invalidation=True)
    → Evaluates all preconditions on refreshed snapshot
    → Explicitly requests Copilot review on new squashed HEAD
```

### What Did NOT Change

- `invalidates_snapshot=True` is still set by `SquashAction` — the HEAD genuinely
  changes after squash, so the snapshot must be refreshed.
- `runs_after_invalidation=True` on `RequestReviewAction` is retained — this is the
  correct mechanism for ensuring review is requested on the new HEAD.
- The pipeline runner's invalidation logic is unchanged — it correctly skips non-opt-in
  actions and refreshes the snapshot for opt-in actions.

## Acceptance Criteria

- [x] `SquashAction` does not rely on triggering Copilot review as a side effect
- [x] `RequestReviewAction` always explicitly requests review after squash (on new HEAD)
- [x] `squash_post_repair()` no longer contains review-requesting logic
- [x] Spec language corrected to remove "force-push triggers review" assumptions
- [x] Pipeline, documentation, and specs updated to match this workflow
