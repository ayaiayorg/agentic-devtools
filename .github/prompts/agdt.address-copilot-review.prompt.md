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

- Confirm the URL matches the expected pattern.
- If the URL is malformed or missing, **stop** and ask the user for a valid URL.

---

## Phase 2: Fetch Review Comments

Retrieve all comments belonging to this specific review using the GitHub REST API.

### Command

```bash
gh api "repos/{owner}/{repo}/pulls/{pr_number}/reviews/{review_id}/comments?per_page=100"
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
complete, commit and push once (not per-comment).

### Commit & Push

```bash
agdt-git-save-work --commit-message "fix([#<issue>](https://github.com/{owner}/{repo}/issues/<issue>)): address copilot review feedback

- <summary of changes>

[#<issue>](https://github.com/{owner}/{repo}/issues/<issue>)"
agdt-task-wait
```

> If no GitHub issue is linked to the PR, use the PR number in the commit scope or
> ask the user for the issue number.

### Capture the Commit Hash

```bash
COMMIT_FULL=$(git log -1 --format="%H")
COMMIT_SHORT=$(git log -1 --format="%h")
```

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

---

## Phase 6: Resolve Review Threads

After all replies are posted, resolve the corresponding discussion threads using GraphQL.

### Step 1 — Map Comment IDs to Thread IDs

```bash
gh api graphql -f query='query {
  repository(owner: "{owner}", name: "{repo}") {
    pullRequest(number: {pr_number}) {
      reviewThreads(first: 100) {
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

---

## Phase 7: Re-request Copilot Review

Request a new review from the Copilot reviewer bot so it can verify the changes.

```bash
gh api "repos/{owner}/{repo}/pulls/{pr_number}/requested_reviewers" \
  -X POST -f 'reviewers[]=copilot-pull-request-reviewer[bot]'
```

The Copilot reviewer's login is always `copilot-pull-request-reviewer[bot]`.

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

### Status

- [x] All comments replied to
- [x] All threads resolved
- [x] Copilot re-review requested
- [x] Commit: {COMMIT_SHORT} (if changes were made)
```

---

## Error Handling

- **API rate limits**: If `gh api` returns a 403/429, wait and retry.
- **Thread already resolved**: Skip silently — the GraphQL mutation is idempotent.
- **Comment reply fails**: Log the error, continue with the remaining comments, and
  report failures in the summary.
- **No comments found**: If the review has zero comments, inform the user and stop.
