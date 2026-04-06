# PR Merge Orchestrator

You are orchestrating the merge of pull request **{{pull_request_id}}**.

## Configuration

- **Merge strategy**: {{merge_strategy}}
- **Delete branch after merge**: {{merge_delete_branch}}
- **Poll interval**: {{merge_poll_interval_seconds}} seconds
- **Max cycles**: {{merge_max_cycles}}
- **Auto-merge**: {{merge_auto_merge}}

## State Machine

This workflow follows a deterministic state machine:

```text
INIT -> POLL -> ADDRESS_REVIEW (optional) -> WAIT_REVIEW -> READY_TO_MERGE -> APPROVE -> MERGE -> VERIFY -> DONE
```

With `BLOCKED` as a terminal failure state.

## Workflow Steps

### 1. Poll PR State

Check the current PR state including:
- Open/closed/merged status
- Latest head SHA
- Mergeability
- Required checks status
- Latest Copilot review outcome on current head SHA

### 2. Decision Logic

At each poll cycle, apply this precedence:

1. **BLOCKED** — merge conflicts, PR closed, locked, or unrecoverable error
2. **ADDRESS_REVIEW** — latest Copilot review on current head has comments
   (including suppressed/hidden/minimized)
3. **READY_TO_MERGE** — latest Copilot review has zero comments and all
   required checks are green
4. **WAIT_REVIEW** — awaiting review completion or check results

### 3. Idempotency

Track `(head_sha, review_id)` pairs. Do not reprocess the same pair.
Context keys:
- `last_processed_head_sha`
- `last_processed_review_id`
- `cycle_count`

### 4. Address Review

When Copilot review has comments, delegate to `/agdt.address-copilot-review`
with the review URL. After addressing, a new head SHA is expected before
resuming merge evaluation.

### 5. Approve and Merge

When all gates are green:
1. Ensure PR is not a draft (publish if allowed)
2. Approve the PR
3. Merge using the configured strategy
4. Optionally delete the source branch

### 6. Verification

After merge:
- Confirm PR state is merged
- Capture merge commit SHA and timestamps
- Emit machine-readable summary

## Next Step

Begin by polling the PR state using GitHub CLI:

```bash
gh pr view {{pull_request_id}} --json state,mergedAt,locked,mergeable,mergeStateStatus,headRefOid
```

Then proceed based on the decision logic above.
