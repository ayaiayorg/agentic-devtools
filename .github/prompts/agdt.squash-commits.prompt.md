# Squash Commits

You are a senior software engineer squashing multiple commits on a feature branch into a single
well-formed commit. Follow this workflow systematically, completing each phase before proceeding
to the next.

---

## Tooling Priority

**Always prefer `agdt-*` commands** from agentic-devtools over raw git commands:

| Operation | Preferred (agdt-*) | Fallback (raw) |
|-----------|-------------------|----------------|
| Run tests | `agdt-test` + `agdt-task-wait` | _Do not run `pytest` directly; always use `agdt-test` commands._ |
| Stage changes | `agdt-git-stage` | `git add` |
| Commit | `agdt-git-save-work` | `git commit` |
| Push (force) | `agdt-git-force-push` | `git push --force-with-lease` |
| List GitHub issues | — | `gh issue list` |

The `agdt-*` commands provide: centralized state tracking, consistent formatting, and background task management.

---

## Phase 1: Context Gathering

Understand the branch state before making any changes.

### Commands

```bash
# Show current branch name
git rev-parse --abbrev-ref HEAD

# Fetch latest main so commit counts and diffs are accurate
git fetch origin main

# Count commits to squash
git rev-list --count origin/main..HEAD

# List all commits on current branch not in origin/main
git log --oneline origin/main..HEAD

# Show commit details with stats
git log --stat origin/main..HEAD

# Show overall diff summary (files changed)
git diff --stat origin/main..HEAD
```

### Output

Document:

- Current branch name
- Number of commits to squash
- Summary of what each commit changed
- Total files affected

### Edge Case: Single Commit

If `git rev-list --count origin/main..HEAD` returns `1`, **no squash is needed**. Inform the user and stop.

### Safety Detection

Before proceeding, detect complex history conditions that require safe mode. Run **all** of the
following checks:

```bash
# 1. Detect merge commits in the branch history
git log --oneline --merges origin/main..HEAD

# 2. Detect divergence between local branch and its remote tracking branch
UPSTREAM=$(git rev-parse --abbrev-ref --symbolic-full-name "@{u}" 2>/dev/null || echo "")
if [ -z "${UPSTREAM}" ]; then
  echo "no remote tracking branch"
else
  REMOTE=${UPSTREAM%%/*}
  REMOTE_BRANCH=${UPSTREAM#*/}
  git fetch "${REMOTE}" "${REMOTE_BRANCH}" 2>/dev/null || echo "warning: could not fetch ${UPSTREAM} (branch may not exist on remote)"
  git rev-list --left-right --count "${UPSTREAM}...HEAD" 2>/dev/null || echo "could not compute divergence against ${UPSTREAM}"
fi

# 3. Check for in-progress cherry-pick or rebase (works in normal repos and worktrees)
test -f "$(git rev-parse --git-path CHERRY_PICK_HEAD)" 2>/dev/null && echo "CHERRY_PICK in progress"
test -f "$(git rev-parse --git-path REBASE_HEAD)" 2>/dev/null && echo "REBASE in progress"
test -d "$(git rev-parse --git-path rebase-merge)" 2>/dev/null && echo "interactive REBASE in progress"
test -d "$(git rev-parse --git-path rebase-apply)" 2>/dev/null && echo "REBASE/AM in progress"
```

**Interpretation:**

| Condition | Detection | Action |
|-----------|-----------|--------|
| Merge commits present | `git log --merges` returns output | **Safe mode ON**: use soft-reset approach only (Phase 3 Approach A). Merge commits fold in history from other branches; interactive rebase will flatten them, losing their merge structure and potentially producing incorrect results. |
| Remote divergence (remote has commits not in local) | `git rev-list --left-right --count` shows a non-zero **left** count for `${UPSTREAM}` (e.g., `2  0` or `2  3` — remote has 2 commits not in local) | **Abort**: do not proceed with squash. Instruct the user to inspect remote-only commits (e.g., `git log --oneline "HEAD..${UPSTREAM}"`), coordinate with collaborators, and reconcile by pulling/rebasing/merging or otherwise updating the local branch so that it contains all remote commits before restarting the squash workflow. Proceeding would overwrite those remote-only commits on force-push. |
| Remote divergence (local-only, no remote-ahead) | `git rev-list --left-right --count` shows zero left count but non-zero right count (e.g., `0  3` — local has 3 commits not in remote) | **OK**: this is normal for a feature branch with local-only commits. No action needed. |
| Cherry-pick / rebase in progress | Sentinel files exist | **Abort**: do not proceed with squash. Instruct the user to complete or abort the in-progress operation first (`git cherry-pick --abort`, `git rebase --abort`). |

If **any** safe-mode condition is detected (e.g., merge commits present), print a clear warning:

```text
⚠️  SAFE MODE ACTIVATED
Detected: [merge commits | ...]
Using soft-reset approach to preserve content integrity.
```

### Pre-Squash Baseline Capture

**Always** capture the pre-squash diff baseline before any history rewriting. This baseline is
used in Phase 4 to verify that the squash did not alter the effective change set.

```bash
# Record the merge-base with the target branch
MERGE_BASE=$(git merge-base origin/main HEAD)
echo "Merge base: ${MERGE_BASE}"

# Record current HEAD SHA
PRE_SQUASH_SHA=$(git rev-parse HEAD)
echo "Pre-squash HEAD: ${PRE_SQUASH_SHA}"

# Compute a hash of the full binary diff (content fingerprint)
PRE_DIFF_HASH=$(git diff --binary "${MERGE_BASE}"..HEAD | git hash-object --stdin)
echo "Pre-squash diff hash: ${PRE_DIFF_HASH}"

# Capture diff stats for human-readable comparison
PRE_STATS=$(git diff --stat "${MERGE_BASE}"..HEAD)
echo "Pre-squash stats:"
echo "${PRE_STATS}"
```

Save these values — they are required for the equivalence check in Phase 4.

---

## Phase 2: Commit Message Composition

Compose a single commit message following this repo's [Conventional Commits convention](../../COMMIT_CONVENTION.md) before squashing.

### Determine the GitHub Issue Number

The commit message **requires** a GitHub issue link as the scope. Try these strategies in order:

1. **Check the branch name** for an issue number (e.g., `feature/123-add-webhook` or `fix/42-null-guard`).
2. **Check existing commit messages** on the branch for issue references (`#NNN`).
3. **Check for an open PR** linked to this branch — the PR description often contains the issue link:

   ```bash
   gh pr view --json title,body,url 2>/dev/null || echo "No PR found for this branch"
   ```

4. **Search recent GitHub issues** to find the matching issue:

   ```bash
   # List recent open issues
   gh issue list --limit 20

   # Search by keyword from the branch name or commit summaries
   gh issue list --search "<keyword>"
   ```

5. **Ask the user** if none of the above yields a result.

### Message Format

Follow the [COMMIT_CONVENTION.md](../../COMMIT_CONVENTION.md):

```text
type([#NNN](https://github.com/ayaiayorg/agentic-devtools/issues/NNN)): <short summary>

- <notable change 1>
- <notable change 2>
- <notable change 3>

[#NNN](https://github.com/ayaiayorg/agentic-devtools/issues/NNN)
```

**Rules:**

- The **scope** is always a GitHub issue markdown link — never omit it
- The **footer** must repeat the same issue link(s) from the scope
- Use the correct **type** (`feat`, `fix`, `docs`, `refactor`, `test`, `chore`, etc.)
- For parent/child issues: `type([#10](url)/[#42](url)): summary` (parent first)
- Summary line: imperative mood, concise (≤72 chars)
- Body: bullet list of **notable** changes (not every minor edit — group related changes)

### Output

Present the composed commit message for confirmation before proceeding.

---

## Phase 3: Squash Execution

Use one of the two approaches below. **If safe mode was activated in Phase 1, you MUST use
Approach A** — interactive rebase does not handle merge commits or diverged history correctly.

### Approach A: Soft Reset (Recommended — Required in Safe Mode)

Simpler and handles merge commits cleanly. Use the `MERGE_BASE` SHA captured in Phase 1 as the
reset target — **not** `origin/main` directly — to avoid staging unintended reversions if
`origin/main` has advanced since the branch was created.

```bash
# Soft reset to the captured merge-base — keeps all changes staged
# (using MERGE_BASE from Phase 1 ensures we reset to the PR's actual base)
git reset --soft "${MERGE_BASE}"

# Preferred: use agentic-devtools with a multi-line commit message
# After soft reset, skip auto-stage/rebase/push — the force-push happens in Phase 5
agdt-set commit_message "<composed message>"
agdt-set skip_stage true
agdt-set skip_push true
agdt-git-save-work --skip-rebase

# Fallback: use git's editor directly for a multi-line message
# (omit -m so you can enter subject, body, and footer properly)
git commit
```

### Approach B: Interactive Rebase

Use **only** when the history is linear (no merge commits, no divergence) and you need finer
control over individual commits. **Do not use this approach if safe mode was activated.**

```bash
# Interactive rebase against the captured merge-base (NOT origin/main directly,
# which may have advanced and would change the PR's merge-base and diff)
git rebase -i "${MERGE_BASE}"

# In the editor:
# - Keep the first commit as "pick"
# - Change all subsequent commits to "squash" (or "s")
# - Save and close
# - Replace the combined message with the composed message
```

### After Squashing

```bash
# Verify the squash produced exactly one commit ahead of origin/main
git rev-list --count origin/main..HEAD

# Show the final commit
git log -1 --stat
```

---

## Phase 4: Verification

Verify that no changes were lost, the result is correct, and the diff is content-equivalent to
the pre-squash state.

### Checklist

```bash
# 1. Verify working tree is clean
git status

# 2. Verify exactly one commit ahead of origin/main
git rev-list --count origin/main..HEAD

# 3. Verify all changes are preserved (informational — latest-main context only;
#    the strict equivalence checks below use ${MERGE_BASE}, not origin/main)
git diff origin/main..HEAD --stat

# 4. Verify commit message follows conventions
git log -1 --format="%B"

# 5. Verify the merge-base has not changed (ensures the PR base is stable)
CURRENT_MERGE_BASE=$(git merge-base origin/main HEAD)
[ "${CURRENT_MERGE_BASE}" = "${MERGE_BASE}" ] && echo "OK: merge-base unchanged" || echo "WARNING: merge-base changed from ${MERGE_BASE} to ${CURRENT_MERGE_BASE}"
```

### Patch-Equivalence Check

**This check is mandatory.** Compare the post-squash diff against the pre-squash baseline
captured in Phase 1 to ensure the effective change set has not been altered.

```bash
# Sanity check: recompute the merge-base and warn if it changed
POST_MERGE_BASE=$(git merge-base origin/main HEAD)
if [ "${POST_MERGE_BASE}" != "${MERGE_BASE}" ]; then
    echo "WARNING: merge-base changed from ${MERGE_BASE} to ${POST_MERGE_BASE}."
    echo "Using original MERGE_BASE for diff comparison to keep checks stable."
fi

# Record post-squash HEAD SHA
POST_SQUASH_SHA=$(git rev-parse HEAD)

# Compute post-squash diff hash using the SAME base as Phase 1 (not the recomputed one)
POST_DIFF_HASH=$(git diff --binary "${MERGE_BASE}"..HEAD | git hash-object --stdin)
echo "Post-squash diff hash: ${POST_DIFF_HASH}"

# Capture post-squash stats using the same base
# Note: All verification diffs/hashes in this phase intentionally use the captured
# ${MERGE_BASE} to avoid instability if origin/main advances.
# In particular, the earlier "Verify all changes are preserved" checklist step that
# suggests `git diff origin/main..HEAD --stat` MUST be treated as informational only
# (latest-main context). The strict equivalence checks are:
#   - PRE_DIFF_HASH vs POST_DIFF_HASH (both from ${MERGE_BASE}..HEAD)
#   - PRE_STATS vs POST_STATS (both from ${MERGE_BASE}..HEAD)
POST_STATS=$(git diff --stat "${MERGE_BASE}"..HEAD)
echo "Post-squash stats:"
echo "${POST_STATS}"

# Compare diff hashes
if [ "${PRE_DIFF_HASH}" = "${POST_DIFF_HASH}" ]; then
    echo "✅ PASS: Diff hashes match — squash is content-equivalent."
else
    echo "❌ FAIL: Diff hashes do NOT match — the squash changed the effective diff!"
    echo "Pre-squash:  ${PRE_DIFF_HASH}"
    echo "Post-squash: ${POST_DIFF_HASH}"
    echo ""
    echo "Investigate the difference before pushing:"
    echo "  git diff ${PRE_SQUASH_SHA} HEAD"
fi
```

If the hashes do **not** match, **do not proceed to Phase 5**. Instead:

1. Investigate what changed: `git diff <pre-squash-SHA> HEAD`
2. Determine if the difference is expected (e.g., merge conflict resolution was intentionally changed)
3. If unexpected, abort and recover using the pre-squash SHA from Phase 1: `git reset --hard <pre-squash-SHA>`

### Verification Report

If the user requested a verification report (e.g., by including `report_file=<filepath>` in their
instructions or specifying a report file path), write a JSON verification report to that file.
This report can be used by CI pipelines or other tools to verify squash integrity programmatically.

```bash
# Only write the report if a filepath was specified
# Construct JSON verification report
cat > "<filepath>" << 'REPORT_EOF'
{
  "merge_base": "<MERGE_BASE value>",
  "pre_squash_sha": "<PRE_SQUASH_SHA value>",
  "post_squash_sha": "<POST_SQUASH_SHA value>",
  "pre_diff_hash": "<PRE_DIFF_HASH value>",
  "post_diff_hash": "<POST_DIFF_HASH value>",
  "pre_stats": "<PRE_STATS summary line>",
  "post_stats": "<POST_STATS summary line>",
  "equivalent": true_or_false,
  "warnings": ["list of any warnings from safety detection"]
}
REPORT_EOF
```

Replace the placeholder values with the actual captured values. Set `"equivalent"` to `true` if
the diff hashes match, `false` otherwise. Include any warnings from the safety detection phase
(e.g., `"merge commits detected"`, `"remote divergence detected"`).

### Run Tests

```bash
# Use agentic-devtools (always — do not run pytest directly)
agdt-test
agdt-task-wait
```

### Verification Summary

Confirm all items pass:

- [ ] All changes from all previous commits are preserved
- [ ] Working tree is clean after squash
- [ ] Exactly one commit ahead of origin/main
- [ ] Commit message follows repo conventions
- [ ] Branch merge-base is unchanged from Phase 1 capture
- [ ] No unintended files staged or lost
- [ ] **Diff hashes match** (pre-squash and post-squash are content-equivalent)
- [ ] Tests pass (if applicable)
- [ ] Verification report written (if a report file was requested)

---

## Phase 5: Push

Force-push the squashed branch (since history was rewritten).

```bash
# Preferred: agentic-devtools (uses --force-with-lease internally)
agdt-git-force-push

# Fallback: Use --force-with-lease for safety (NEVER use bare --force)
git push --force-with-lease
```

> **Important**: Always use `--force-with-lease` (never bare `--force`). `--force-with-lease`
> refuses to push if the remote has commits you haven't seen, preventing accidental overwrites
> of collaborators' work. The `agdt-git-force-push` command already uses `--force-with-lease`
> internally.

---

## Azure DevOps PR Diff Parity

When squashing commits on a branch that has an associated Azure DevOps pull request, it is
critical to understand how AzDO computes the PR diff, and why the equivalence check in Phase 4
uses `git merge-base`.

### How AzDO computes the PR diff

Azure DevOps computes the diff shown in the PR "Files" tab against the **merge-base** of the
source branch and the target branch (typically `main`). This is the same commit that
`git merge-base origin/main HEAD` returns locally.

```text
          A---B---C---D  (feature branch, pre-squash)
         /
    M---N---O            (origin/main)
         \
          S              (feature branch, post-squash, single commit)

    merge-base = N (in both cases)
    AzDO PR diff = diff(N, D) pre-squash
    AzDO PR diff = diff(N, S) post-squash
```

For the PR diff to remain **unchanged** after a squash, `diff(N, D)` and `diff(N, S)` must be
identical. This is exactly what the Phase 4 equivalence check verifies by comparing diff hashes
computed against the merge-base.

### Why this matters

1. **Reviewer trust**: Reviewers approved `diff(N, D)`. If `diff(N, S)` differs, the approval
   may be stale or invalid — the reviewer saw different content than what will be merged.
2. **Merge commit contamination**: If the branch contains merge commits (e.g., merging `main`
   into the feature branch), those commits pull in changes from `main` that inflate the diff.
   The soft-reset approach (Phase 3 Approach A) correctly collapses these into the intended
   change set because it resets softly to the captured merge-base SHA (from Phase 1),
   e.g. `git reset --soft "${MERGE_BASE}"`, which preserves only the working tree delta
   against the PR base.
3. **Diverged remote**: If the remote tracking branch has diverged (e.g., a collaborator pushed
   additional commits), the local squash may be based on a different state than the remote. Phase 1
   surfaces this remote-ahead divergence so you can explicitly decide whether overwriting those
   remote commits is acceptable before proceeding. The `--force-with-lease` in Phase 5 only
   protects against _unexpected_ new commits that appear on the remote **after** your last
   `git fetch` — it does not prevent overwriting commits you already fetched and chose to ignore.

### Key rule

> The equivalence check MUST compute diffs against the captured `git merge-base origin/main HEAD`
> SHA, NOT against `origin/main` directly. `git diff` interprets `A..B` as a diff between two
> endpoints — it does not compute a merge-base. By explicitly capturing the merge-base SHA before
> the squash and diffing against it both before and after, the check remains consistent even if
> `origin/main` advances between the two measurements.

---

## After Squash

Your branch history is now clean and the single squashed commit has already been created and
pushed in the previous phases. No additional `agdt-git-save-work` or `git commit` commands are
required at this point.

If you still have uncommitted local changes, return to the earlier commit phase and use the
appropriate commit step _before_ pushing.
