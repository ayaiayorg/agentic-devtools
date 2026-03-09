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

# Count commits to squash
git rev-list --count main..HEAD

# List all commits on current branch not in main
git log --oneline main..HEAD

# Show commit details with stats
git log --stat main..HEAD

# Show overall diff summary (files changed)
git diff --stat main..HEAD
```

### Output

Document:

- Current branch name
- Number of commits to squash
- Summary of what each commit changed
- Total files affected

### Edge Case: Single Commit

If `git rev-list --count main..HEAD` returns `1`, **no squash is needed**. Inform the user and stop.

### Edge Case: Merge Commits

If `git log --oneline main..HEAD` shows merge commits (lines starting with `Merge`), prefer the **soft reset** approach in Phase 3 over interactive rebase to avoid complications.

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

Use one of the two approaches below.

### Approach A: Soft Reset (Recommended)

Simpler and handles merge commits cleanly:

```bash
# Soft reset to main — keeps all changes staged
git reset --soft main

# Preferred: use agentic-devtools with a multi-line commit message
agdt-set commit_message "<composed message>"
agdt-git-save-work

# Fallback: use git's editor directly for a multi-line message
# (omit -m so you can enter subject, body, and footer properly)
git commit
```

### Approach B: Interactive Rebase

Use when you need finer control over individual commits:

```bash
# Interactive rebase against main
git rebase -i main

# In the editor:
# - Keep the first commit as "pick"
# - Change all subsequent commits to "squash" (or "s")
# - Save and close
# - Replace the combined message with the composed message
```

### After Squashing

```bash
# Verify the squash produced exactly one commit ahead of main
git rev-list --count main..HEAD

# Show the final commit
git log -1 --stat
```

---

## Phase 4: Verification

Verify that no changes were lost and the result is correct.

### Checklist

```bash
# 1. Verify working tree is clean
git status

# 2. Verify exactly one commit ahead of main
git rev-list --count main..HEAD

# 3. Verify all changes are preserved (should show NO output if nothing was lost)
git diff main..HEAD --stat

# 4. Verify commit message follows conventions
git log -1 --format="%B"

# 5. Verify branch still points to correct parent
git merge-base --is-ancestor main HEAD && echo "OK: main is ancestor" || echo "ERROR: main is not ancestor"
```

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
- [ ] Exactly one commit ahead of main
- [ ] Commit message follows repo conventions
- [ ] Branch still points to correct parent (main is ancestor)
- [ ] No unintended files staged or lost
- [ ] Tests pass (if applicable)

---

## Phase 5: Push

Force-push the squashed branch (since history was rewritten).

```bash
# Preferred: agentic-devtools (force push for rewritten history)
agdt-git-force-push

# Fallback: Use --force-with-lease for safety
git push --force-with-lease
```

> **Note**: `--force-with-lease` is safer than `--force` because it will refuse to push if the remote has commits you haven't seen, preventing accidental overwrites of collaborators' work.

---

## After Squash

Your branch history is now clean and the single squashed commit has already been created and
pushed in the previous phases. No additional `agdt-git-save-work` or `git commit` commands are
required at this point.

If you still have uncommitted local changes, return to the earlier commit phase and use the
appropriate commit step _before_ pushing.
