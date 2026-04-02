# Address Copilot PR Review Comments

You are a senior software engineer addressing feedback from a GitHub Copilot pull request review.
Follow this workflow systematically, completing each phase before proceeding to the next.

---

## Tooling Priority

**Always prefer `agdt-*` commands** from agentic-devtools over raw alternatives:

| Operation | Preferred (agdt-*) | Fallback (raw) |
|-----------|-------------------|----------------|
| Run tests | `agdt-test` + `agdt-task-wait` | _Do not run `pytest` directly; always use `agdt-test` commands._ |
| Stage changes | `agdt-git-stage` | `git add` |
| Commit & push | `agdt-git-save-work` | `git commit` + `git push` |
| Force push | `agdt-git-force-push` | `git push --force-with-lease` |

The `agdt-*` commands provide: centralized state tracking, consistent formatting, and background
task management.

---

## Phase 1: Parse the Review URL

Extract identifiers from the PR review URL provided as input.

### Expected URL Format

```text
https://github.com/{owner}/{repo}/pull/{pr_number}#pullrequestreview-{review_id}
```

### Parse Out

| Variable | Example |
|----------|---------|
| `owner` | `ayaiayorg` |
| `repo` | `agentic-devtools` |
| `pr_number` | `1009` |
| `review_id` | `4019856282` |

### Validation

- Confirm the URL matches the expected pattern (note: the fragment uses
  `pullrequestreview-` — singular, not plural).
- If the URL is malformed or missing, **stop** and ask the user for a valid URL.

---

## Phase 2: Fetch Review Comments

Retrieve all comments belonging to this specific review using the GitHub REST API.

Reviews can exceed 100 comments, so you **must** handle pagination.

### Command

```bash
# Use --paginate to ensure ALL pages of comments are fetched, not just the first 100
gh api --paginate \
  "repos/{owner}/{repo}/pulls/{pr_number}/reviews/{review_id}/comments" \
  --jq '.[]'
```

### Relevant Fields per Comment

| Field | Use |
|-------|-----|
| `id` | Database ID — needed for replying and mapping to GraphQL thread IDs |
| `path` | File path the comment is on |
| `line` | Line number (may be `null` for file-level comments) |
| `body` | Full comment text (the reviewer's feedback) |
| `diff_hunk` | The diff context the comment was placed on |

### Output

List each comment with its `id`, `path`, `line`, and a short excerpt of `body` so you can
see what needs addressing.

---

## Phase 3: Triage Each Comment

For each comment, read the `body` and `diff_hunk` to understand the reviewer's request.
Also read the referenced file(s) in the working tree to understand the current state.

### Classification

| Category | Criteria | Action |
|----------|----------|--------|
| **Addressable** | The feedback is valid and a code/doc change will fix it | Make a change in the relevant file |
| **Not addressable** | False positive, already correct, out of scope, or should not result in a change | Reply with a clear explanation |

### Output

Document a triage table:

```markdown
| Comment ID | File | Line | Category | Reason |
|------------|------|------|----------|--------|
| 12345 | src/foo.py | 42 | Addressable | Valid: missing null check |
| 12346 | README.md | 10 | Not addressable | Already correct — GitHub diff rendering artifact |
```

---

## Phase 4: Make Changes for Addressable Comments

Edit files to address every comment classified as **addressable**. After **all** edits are
complete, verify with tests, then commit and push once (not per-comment).

### Verify Changes

Run the test suite before committing to ensure edits don't break anything:

```bash
agdt-test
agdt-task-wait
```

If tests fail, fix the issues before proceeding.

### Resolve the GitHub Issue Key

Before committing, determine the GitHub issue linked to this PR so your commit message
follows the repository's required convention (issue link in the scope and footer).

1. Check the **existing commit message** on the branch (if any) for an issue reference
   like `#1062` in the conventional-commit scope.
2. If not found there, check the **PR title** and **PR body** for closing keywords
   (`closes #N`, `fixes #N`, `resolves #N`) or issue links.
3. If still not found, check the PR's **linked issues** via the GitHub API:

   ```bash
   gh api graphql -f query='query {
     repository(owner: "{owner}", name: "{repo}") {
       pullRequest(number: {pr_number}) {
         closingIssuesReferences(first: 10) {
           nodes { number title }
         }
       }
     }
   }'
   ```

4. The resolved issue number will be used in the commit message scope and footer
   (see Commit & Push below). No state key needs to be set — include the issue
   link directly in the commit message.

5. If **no** issue can be determined after all checks, **create a GitHub issue first**
   (required by this repo's commit convention — every commit must have an issue link
   in the scope and footer). Then use the newly created issue number.

### Commit & Push

When a GitHub issue **was** resolved:

```bash
agdt-set commit_message "<type>([#<issue>](https://github.com/{owner}/{repo}/issues/<issue>)): address copilot review feedback

- <summary of changes>

[#<issue>](https://github.com/{owner}/{repo}/issues/<issue>)"
agdt-set dry_run false
agdt-set skip_stage false
agdt-set skip_push false
agdt-set skip_rebase false
agdt-git-save-work
agdt-task-wait
```

When you **don't yet have** a GitHub issue:

1. **Create or link a GitHub issue first** (required by this repo's commit convention).
2. Then use the same commit-message pattern as above, including the issue link in both the scope and footer:

```bash
agdt-set commit_message "<type>([#<issue>](https://github.com/{owner}/{repo}/issues/<issue>)): address copilot review feedback

- <summary of changes>

[#<issue>](https://github.com/{owner}/{repo}/issues/<issue>)"
agdt-set dry_run false
agdt-set skip_stage false
agdt-set skip_push false
agdt-set skip_rebase false
agdt-git-save-work
agdt-task-wait
```

Choose the commit **type** based on the nature of the changes:

| Type | When to use |
|------|-------------|
| `fix` | Bug fixes, incorrect behavior |
| `refactor` | Code quality, readability, or structure improvements |
| `style` | Formatting, naming, whitespace changes |
| `docs` | Documentation-only changes |
| `chore` | Maintenance tasks that don't affect production code |

### Capture the Commit Hash

```bash
COMMIT_FULL=$(git log -1 --format="%H")
COMMIT_SHORT=$(git log -1 --format="%h")
```

### Verify Push Was Successful

After `agdt-git-save-work` completes, confirm the local commit was pushed to the
remote and that the PR head now matches:

```bash
REMOTE_SHA=$(gh pr view {pr_number} --repo {owner}/{repo} --json headRefOid --jq '.headRefOid')
REMOTE_SHA_SHORT=$(echo "$REMOTE_SHA" | cut -c1-7)
```

Compare `REMOTE_SHA` with `COMMIT_FULL`. If they do not match:

1. Print `⚠️ Push verification failed — remote head ({REMOTE_SHA_SHORT}) ≠ local ({COMMIT_SHORT}). Retrying push.`
2. Run `agdt-git-force-push` and `agdt-task-wait`.
3. Re-verify with the same `gh pr view` command.
4. If the SHAs still do not match after the retry, **stop** and report the failure
   to the user.

### Edge Case: No Addressable Comments

If every comment was triaged as **not addressable**, skip the commit step and proceed
directly to Phase 5 (replies only).

---

## Phase 5: Reply to Every Comment

Send a reply to **each** comment from the review.

### For Comments That WERE Addressed

Use this reply template (with the actual commit hash from Phase 4):

```text
addressed in [{COMMIT_SHORT}](https://github.com/{owner}/{repo}/pull/{pr_number}/commits/{COMMIT_FULL})
```

### For Comments That Were NOT Addressed

Reply with a clear, specific explanation of **why** the feedback was not applied. Examples:

- "The tables already use standard single-pipe format (`| ... |`). The double-pipe
  rendering may be a GitHub diff display artifact — the raw markdown is correct."
- "This is already handled by the existing `validate()` call on line 45 — no change needed."
- "This would be a breaking change outside the scope of this PR. Filed as
  {owner}/{repo}#NNN to track separately."

### Sending Replies via REST API

For each comment, post a reply:

```bash
gh api "repos/{owner}/{repo}/pulls/{pr_number}/comments/{comment_id}/replies" \
  -f body="<reply text>"
```

### Verify Replies Were Posted

After posting all replies, verify each one was actually created:

```bash
gh api --paginate \
  "repos/{owner}/{repo}/pulls/{pr_number}/reviews/{review_id}/comments" \
  --jq '.[] | {id, in_reply_to_id, body}' | jq -s '.'
```

For each comment you replied to, confirm that a child reply exists (a comment whose
`in_reply_to_id` matches the original comment's `id`). If any reply is missing:

1. Print `⚠️ Reply to comment {comment_id} was not found — retrying.`
2. Retry the POST for that specific comment (up to 2 retries).
3. Re-verify after each retry.
4. If the reply still cannot be confirmed after retries, log the failure and
   continue — report it in the Phase 8 summary.

---

## Phase 6: Resolve Review Threads

After all replies are posted, resolve the corresponding discussion threads using GraphQL.

### Step 1 — Map Comment IDs to Thread IDs

PRs can have more than 100 review threads, so you **must** paginate using `pageInfo`
and `endCursor`. Fetch pages until `hasNextPage` is `false`.

```bash
# First page (adjust "after" cursor for subsequent pages)
gh api graphql -f query='query {
  repository(owner: "{owner}", name: "{repo}") {
    pullRequest(number: {pr_number}) {
      reviewThreads(first: 100) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          isResolved
          comments(first: 1) {
            nodes { databaseId }
          }
        }
      }
    }
  }
}'
```

If `pageInfo.hasNextPage` is `true`, fetch the next page by adding
`after: "{endCursor}"` to the `reviewThreads` arguments. Repeat until all
threads are collected.

Filter the results to threads whose first comment `databaseId` is in the set of comment
IDs from Phase 2, and that are **not already resolved**.

### Step 2 — Resolve Each Thread

```bash
gh api graphql -f query='mutation {
  resolveReviewThread(input: {threadId: "{thread_id}"}) {
    thread { id isResolved }
  }
}'
```

### Step 3 — Verify All Threads Are Resolved

After resolving all threads, re-fetch the review threads to confirm resolution:

```bash
gh api graphql -f query='query {
  repository(owner: "{owner}", name: "{repo}") {
    pullRequest(number: {pr_number}) {
      reviewThreads(first: 100) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          isResolved
          comments(first: 1) {
            nodes { databaseId }
          }
        }
      }
    }
  }
}'
```

Paginate as in Step 1. Filter to threads whose first comment `databaseId` is in the
set of comment IDs from Phase 2. For each thread that **should** be resolved but is
not (`isResolved == false`):

1. Print `⚠️ Thread {thread_id} is still unresolved — retrying.`
2. Re-run the `resolveReviewThread` mutation (up to 2 retries).
3. Re-verify after each retry.
4. If the thread still cannot be resolved after retries, log the failure and
   report it in the Phase 8 summary.

---

## Phase 7: Re-request Copilot Review

Request a new review from the Copilot reviewer bot so it can verify the changes.

```bash
gh api "repos/{owner}/{repo}/pulls/{pr_number}/requested_reviewers" \
  -X POST -f 'reviewers[]=copilot-pull-request-reviewer[bot]'
```

The Copilot reviewer's login is always `copilot-pull-request-reviewer[bot]`.

### Verify Review Was Requested

After requesting the review, confirm the request was registered:

```bash
gh api "repos/{owner}/{repo}/pulls/{pr_number}/requested_reviewers" \
  --jq '[.users[].login]'
```

Check that `copilot-pull-request-reviewer[bot]` appears in the returned array.
If it does not:

1. Print `⚠️ Copilot review request not confirmed — retrying.`
2. Re-send the POST request (up to 2 retries).
3. Re-verify after each retry.
4. If the reviewer still does not appear after retries, log the failure and
   report it in the Phase 8 summary. The merge-manager parent loop will detect
   the missing review in its next iteration and can recover.

---

## Phase 8: Summary

After completing all phases, present a summary to the user:

```markdown
## Copilot Review Comment Resolution Summary

**PR:** {owner}/{repo}#{pr_number}
**Review ID:** {review_id}
**Total comments:** X

### Results

| Comment ID | File | Line | Category | Action Taken |
|------------|------|------|----------|--------------|
| 12345 | src/foo.py | 42 | Addressed | Fixed in {COMMIT_SHORT} |
| 12346 | README.md | 10 | Not addressed | Already correct (explained) |

### Verification

| Step | Status | Details |
|------|--------|---------|
| Push to remote | ✅ Verified | Head SHA matches {COMMIT_SHORT} |
| Replies posted | ✅ Verified | All X replies confirmed |
| Threads resolved | ✅ Verified | All Y threads resolved |
| Copilot re-review requested | ✅ Verified | Reviewer appears in requested list |

### Status

- [x] All comments replied to (verified)
- [x] All threads resolved (verified)
- [x] Copilot re-review requested (verified)
- [x] Commit: {COMMIT_SHORT} (push verified)
```

---

## Error Handling

- **API rate limits**: If `gh api` returns a 403/429, wait and retry.
- **Thread already resolved**: Skip silently — the GraphQL mutation is idempotent.
- **Comment reply fails**: Log the error, continue with the remaining comments, and
  report failures in the summary.
- **No comments found**: If the review has zero comments, inform the user and stop.
