# Address Copilot PR Review Comments (CI Repair Mode)

> **CI Repair Mode**: This prompt is designed for automated execution on a
> GitHub-hosted runner. Verification (tests, CI) is delegated to the subsequent
> CI pipeline triggered by the push — this agent does NOT run tests.
>
> **⚠️ SECURITY CONSTRAINTS**:
>
> - Do NOT run `pytest`, `agdt-test`, `agdt-test-quick`, `agdt-test-file`,
>   `agdt-test-pattern`, `bash scripts/*.sh`, or any PR-sourced executable.
> - Do NOT install packages from the PR branch (`pip install .`, `pip install -e .`).
> - Do NOT approve or merge the PR. Your scope is limited to: code changes,
>   comment replies, thread resolution, and re-requesting review.
> - If `AGDT_CI_REPAIR_MODE=1` is set, these constraints are mandatory
>   (defense-in-depth).

You are a senior software engineer addressing feedback from a GitHub Copilot pull
request review and/or CI failures. Follow this workflow systematically, completing
each phase before proceeding to the next.

---

## Tooling Priority

**Always prefer `agdt-*` commands** from agentic-devtools over raw alternatives:

| Operation | Preferred (agdt-*) | Fallback (raw) |
|-----------|-------------------|----------------|
| Reply to review comments | `agdt-gh-reply-to-review-comments` | `gh api .../comments/{id}/replies` per comment |
| Resolve review threads | `agdt-gh-resolve-review-threads` | GraphQL `resolveReviewThread` mutation per thread |
| Request Copilot re-review | `agdt-gh-request-copilot-review` | `gh api .../requested_reviewers -X POST` |
| Stage changes | — | `git add` |
| Commit & push | — | `git commit` + `git push` |
| Force push | — | `git push --force-with-lease` |

> **CI Repair Note**: Because the `agentic-devtools` package is NOT installed on the
> runner (security constraint: no `pip install` from PR branch), only `agdt-gh-*`
> commands that wrap `gh` CLI are available. Git operations (`stage`, `commit`,
> `push`) use raw git commands directly.

The `agdt-gh-*` commands provide: centralized state tracking and consistent formatting.

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
- If the URL is malformed or missing, check environment variables
  `REPAIR_PR_NUMBER`, `REPAIR_REVIEW_URL`, and `REPAIR_HEAD_SHA` for context.

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

> **Note:** This raw `gh api` call is intentionally retained — no `agdt-gh-*`
> command wraps individual comment content fetching.

### Relevant Fields per Comment

| Field | Use |
|-------|-----|
| `id` | Database ID — needed for replying and mapping to GraphQL thread IDs |
| `path` | File path the comment is on |
| `line` | Line number (may be `null` for file-level comments) |
| `body` | Full comment text (the reviewer's feedback) |
| `diff_hunk` | The diff context the comment was placed on |

### Output

List each comment with its `id`, `path`, `line`, and a short excerpt of `body`.

---

## Phase 3: Triage Each Comment

For each comment, read the `body` and `diff_hunk` to understand the reviewer's
request. Also read the referenced file(s) in the working tree to understand the
current state.

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
| 12346 | README.md | 10 | Not addressable | Already correct |
```

---

## Phase 3b: Handle CI Failures (if present)

If CI failure context is provided (see the `## CI Failure Context` section at the
end of this prompt, if present), address those failures:

The CI pipeline gates are:

- `Targeted Checks ✅` — ruff/mypy/test-structure + per-file coverage on changed files (plus markdownlint for changed `.md`)
- `Smart Module Tests ✅` — targeted test execution for affected modules
- `Workflow Tests ✅` — workflow integration tests for workflow-related changes
- `Copilot Review ✅` — automated AI code review

### For Lint Failures (ruff)

> **Note:** Lint/format failures reaching CI are uncommon — the pre-push hook
> enforces `ruff format` and `ruff check` locally. If these failures appear in
> CI, the hook was likely bypassed with `--no-verify` or not enabled
> (`core.hooksPath` not set to `.githooks`).

1. Read the failure messages to identify specific files and violations
2. Apply automated fixes using **only pinned trusted tooling**:

   ```bash
   ruff check --fix .
   ruff format .
   ```

3. Review the changes to ensure they are correct

### For Markdown Lint Failures (markdownlint)

1. Read the failure messages to identify files and rules violated
2. Fix the markdown issues manually (markdownlint-cli2 does not have a
   reliable `--fix` mode for all rules)

### For Test Failures

1. Read the test failure output to understand which tests failed and why
2. Read the failing test code and the code under test
3. Fix the **source code** (not the tests) to make the tests pass
4. Do NOT run the tests yourself — verification is delegated to the
   subsequent CI run

### For Other Failures

1. Read the failure output carefully
2. If the failure is addressable (e.g., type errors, import issues), fix it
3. If the failure is not addressable (e.g., infrastructure issues, flaky
   tests), note it in your summary

---

## Phase 4: Make Changes for Addressable Comments

Edit files to address every comment classified as **addressable** and every
CI failure that is fixable. After **all** edits are complete, commit and push
once (not per-comment).

> **⚠️ DO NOT run tests.** Verification is delegated to the subsequent CI run
> triggered by the push.

### Stage Changes and Secret Scanning Guard

Explicitly stage all changes first, then run the secret scan on the staged diff.
This ensures the scan covers all pending work before committing.

```bash
# Stage all changes explicitly
git add -A

# Scan staged diff for potential secrets
if git diff --cached | grep -iqE '(token|password|secret|api_key|private_key)'; then
  echo 'ABORT: potential secret detected in staged changes'
  exit 1
fi
```

If the guard triggers, review the staged changes and remove any sensitive content
before proceeding.

### Resolve the GitHub Issue Key

Before committing, determine the GitHub issue linked to this PR so your commit
message follows the repository's required convention.

1. Check the **existing commit message** on the branch for an issue reference
   like `#1062` in the conventional-commit scope.
2. If not found, check the **PR title** and **PR body** for closing keywords.
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

### Commit & Push

Include `[ai-repair]` in the commit body so repair commits are identifiable
in git log.

```bash
agdt-set commit_message "<type>([#<issue>](https://github.com/{owner}/{repo}/issues/<issue>)): address copilot review feedback

- <summary of changes>
[ai-repair]

[#<issue>](https://github.com/{owner}/{repo}/issues/<issue>)"
agdt-git-save-work --skip-stage
agdt-task-wait
```

> **Note:** `--skip-stage` is used because changes were already staged in the
> secret scanning guard step above. This prevents re-staging after the scan.

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

After `agdt-git-save-work` completes, confirm the local commit was pushed:

```bash
REMOTE_SHA=$(gh pr view {pr_number} --repo {owner}/{repo} --json headRefOid --jq '.headRefOid')
REMOTE_SHA_SHORT=$(echo "$REMOTE_SHA" | cut -c1-7)
```

Compare `REMOTE_SHA` with `COMMIT_FULL`. If they do not match, run
`agdt-git-force-push` and `agdt-task-wait`, then re-verify.

### Edge Case: No Addressable Comments and No CI Failures

If every comment was triaged as **not addressable** and there are no CI failures
to fix, skip the commit step and proceed directly to Phase 5 (replies only).

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

Use this reply template:

```text
addressed in [{COMMIT_SHORT}](https://github.com/{owner}/{repo}/pull/{pr_number}/commits/{COMMIT_FULL})
```

#### For Comments That Were NOT Addressed

Reply with a clear, specific explanation of **why** the feedback was not applied.

### Post Replies

```bash
agdt-gh-reply-to-review-comments --pr {pr_number} --repo {owner}/{repo} \
  --review-id {review_id} --replies-file replies.json
```

---

## Phase 6: Resolve Review Threads

After all replies are posted, resolve the corresponding discussion threads.

```bash
agdt-gh-resolve-review-threads --pr {pr_number} --repo {owner}/{repo} \
  --review-id {review_id}
```

---

## Phase 7: Re-request Copilot Review

Request a new review from the Copilot reviewer bot so it can verify the changes.

```bash
agdt-gh-request-copilot-review --pr {pr_number} --repo {owner}/{repo}
```

Check the JSON output — if `verified` is `false`, retry once after 10 seconds.

---

## Phase 8: Summary

After completing all phases, present a summary:

```markdown
## CI Repair Summary

**PR:** {owner}/{repo}#{pr_number}
**Review ID:** {review_id}
**Total comments:** X
**CI failures addressed:** Y

### Results

| Comment ID | File | Line | Category | Action Taken |
|------------|------|------|----------|--------------|
| 12345 | src/foo.py | 42 | Addressed | Fixed in {COMMIT_SHORT} |
| 12346 | README.md | 10 | Not addressed | Already correct (explained) |

### Verification

| Step | Status | Details |
|------|--------|---------|
| Push to remote | ✅ Verified | Head SHA matches {COMMIT_SHORT} |
| Replies posted | ✅ Verified | {successful}/{totalReplies} succeeded |
| Threads resolved | ✅ Verified | {threadsResolved} resolved |
| Copilot re-review requested | ✅ Verified | Reviewer confirmed |
```

---

## Error Handling

- **Command failures**: If any `agdt-gh-*` command exits with a non-zero code,
  print the stderr output and handle as described in the relevant phase.
- **Thread already resolved**: `agdt-gh-resolve-review-threads` handles this
  silently.
- **Comment reply fails**: `agdt-gh-reply-to-review-comments` handles retries
  internally.
- **No comments found**: If the review has zero comments and no CI failures,
  inform the user and stop.
