# Address Copilot PR Review Comments

> **Defense-in-depth**: If the environment variable `AGDT_CI_REPAIR_MODE=1` is set,
> skip all test execution steps (Phase 4 test verification). This variable is set
> by the CI repair job to prevent executing untrusted PR code on the runner.

You are a senior software engineer addressing feedback from a GitHub Copilot pull request review.
Follow this workflow systematically, completing each phase before proceeding to the next.

---

## Tooling Priority

**Always prefer `agdt-*` commands** from agentic-devtools over raw alternatives:

| Operation | Preferred (agdt-*) | Fallback (raw) |
|-----------|-------------------|----------------|
| Reply to review comments | `agdt-gh-reply-to-review-comments` | `gh api .../comments/{id}/replies` per comment |
| Resolve review threads | `agdt-gh-resolve-review-threads` | GraphQL `resolveReviewThread` mutation per thread |
| Request Copilot re-review | `agdt-gh-request-copilot-review` | `gh api .../requested_reviewers -X POST` |
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

> **Note:** This raw `gh api` call is intentionally retained — no `agdt-gh-*` command
> wraps individual comment content fetching. The agent needs the raw comment
> `body`, `path`, `line`, and `diff_hunk` fields for triage in Phase 3.

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

### Commit & Push

If **no** issue can be determined after all checks, **create a GitHub issue first**
(required by this repo's commit convention). Then use the newly created issue number.

```bash
agdt-set commit_message "<type>([#<issue>](https://github.com/{owner}/{repo}/issues/<issue>)): address copilot review feedback

- <summary of changes>

[#<issue>](https://github.com/{owner}/{repo}/issues/<issue>)"
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

Send a reply to **each** comment from the review using the
`agdt-gh-reply-to-review-comments` command.

### Prepare the Replies File

Create a JSON file (e.g., `replies.json`) containing one entry per comment:

```json
[
  {"commentId": 12345, "body": "addressed in [abc123d](https://github.com/{owner}/{repo}/pull/{pr_number}/commits/{COMMIT_FULL})"},
  {"commentId": 12346, "body": "Already correct — the raw markdown uses standard single-pipe format."}
]
```

#### For Comments That WERE Addressed

Use this reply template (with the actual commit hash from Phase 4):

```text
addressed in [{COMMIT_SHORT}](https://github.com/{owner}/{repo}/pull/{pr_number}/commits/{COMMIT_FULL})
```

#### For Comments That Were NOT Addressed

Reply with a clear, specific explanation of **why** the feedback was not applied. Examples:

- "The tables already use standard single-pipe format (`| ... |`). The double-pipe
  rendering may be a GitHub diff display artifact — the raw markdown is correct."
- "This is already handled by the existing `validate()` call on line 45 — no change needed."
- "This would be a breaking change outside the scope of this PR. Filed as
  {owner}/{repo}#NNN to track separately."

### Post Replies

```bash
agdt-gh-reply-to-review-comments --pr {pr_number} --repo {owner}/{repo} \
  --review-id {review_id} --replies-file replies.json
```

The command handles posting each reply, verification (confirms replies were created),
and retry logic internally. Check the JSON output for any failures:

- Read `successful` and `failed` counts from the output.
- If `failed > 0`, read `failedDetails` for specific comment IDs that failed.
  Report these in the Phase 8 summary.

---

## Phase 6: Resolve Review Threads

After all replies are posted, resolve the corresponding discussion threads using
the `agdt-gh-resolve-review-threads` command.

```bash
agdt-gh-resolve-review-threads --pr {pr_number} --repo {owner}/{repo} \
  --review-id {review_id}
```

The command handles:

- Mapping comment IDs to thread IDs via GraphQL (with cursor pagination for >100 threads)
- Resolving each thread via the `resolveReviewThread` GraphQL mutation
- Verifying all threads were resolved
- Retry logic for failed resolutions

Check the JSON output:

- Read `threadsResolved` and `threadsFailed` from the command output JSON. If you need the persisted state values instead, use `agdt-get github.threads_resolved_count` and `agdt-get github.threads_failed_count`.
- If `threadsFailed` is greater than 0, report the failed thread resolutions in the Phase 8 summary.

---

## Phase 7: Re-request Copilot Review

Request a new review from the Copilot reviewer bot so it can verify the changes.

```bash
agdt-gh-request-copilot-review --pr {pr_number} --repo {owner}/{repo}
```

The command handles the POST request, verification (confirms the reviewer appears
in the requested reviewers list), and retry logic internally.

Check the JSON output:

- Read `requested` and `verified` fields.
- If `verified` is `false`, retry the request once:
  1. Wait 10 seconds, then re-run `agdt-gh-request-copilot-review`.
  2. If `verified` is still `false` after the retry, report the failure in the
     Phase 8 summary and instruct the user to investigate manually — do **not**
     assume the merge-manager loop will recover automatically, as it only polls
     for readiness and does not re-request reviews.

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
| Replies posted | ✅ Verified | `agdt-gh-reply-to-review-comments`: {successful}/{totalReplies} succeeded |
| Threads resolved | ✅ Verified | `agdt-gh-resolve-review-threads`: {threadsResolved} resolved |
| Copilot re-review requested | ✅ Verified | `agdt-gh-request-copilot-review`: reviewer confirmed |

### Status

- [x] All comments replied to (verified by `agdt-gh-reply-to-review-comments`)
- [x] All threads resolved (verified by `agdt-gh-resolve-review-threads`)
- [x] Copilot re-review requested (verified by `agdt-gh-request-copilot-review`)
- [x] Commit: {COMMIT_SHORT} (push verified)
```

---

## Error Handling

- **Command failures**: If any `agdt-gh-*` command exits with a non-zero code,
  print the stderr output and handle as described in the relevant phase. The
  commands handle their own retries and rate limiting internally.
- **Thread already resolved**: `agdt-gh-resolve-review-threads` handles this
  silently — already-resolved threads are counted in `github.threads_already_resolved_count`.
- **Comment reply fails**: `agdt-gh-reply-to-review-comments` handles retries
  internally. Any remaining failures are reported in its JSON output — include
  them in the Phase 8 summary.
- **No comments found**: If the review has zero comments, inform the user and stop.
