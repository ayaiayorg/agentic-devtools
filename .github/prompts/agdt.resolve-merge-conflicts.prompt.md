# Resolve Merge Conflicts

You are a senior software engineer resolving merge conflicts. Follow this workflow systematically, completing each phase before proceeding to the next. Ensure no content from either branch is lost.

---

## Tooling Priority

**Always prefer `agdt-*` commands** from agentic-devtools over raw git commands:

| Operation | Preferred (agdt-*) | Fallback (raw) |
|-----------|-------------------|----------------|
| Stage changes (new/modified files) | `agdt-git-stage` | `git add .` |
| Stage all + commit + push | `agdt-git-save-work` | `git add -A` + `git commit` + `git push` |
| Get PR context | — | `gh pr view` |
| List GitHub issues | — | `gh issue list` |

The `agdt-*` commands provide: state tracking, consistent formatting, and background task management.

> `agdt-git-save-work` stages changes via `git add .` (run it from the repo root to cover the whole repo; note that `git add .` does **not** stage deletions), then commits/amends and pushes.
> `agdt-git-stage` likewise stages via `git add .` (repo-root recommended; deletions require `git add -A` or `git add -u`).
> For selective/full-repo staging (including deletions), run `git add <file>` (or `git add -A`) and then `agdt-git-save-work --skip-stage`.
> After running `agdt-git-save-work`, you MUST wait with `agdt-task-wait` for the push + pre-push hook checks to finish.
> See `.github/instructions/pre-push-hook.instructions.md` for the push-fix-push loop pattern.

---

## Phase 1: Discovery

Identify all files with merge conflicts.

### Commands

```bash
# List all conflicted files
git diff --name-only --diff-filter=U

# Alternative: Show conflicted files with status markers
git status --short --unmerged

# Show full status for context
git status
```

### Output

Create a list of all conflicted files with their paths. Note the total count for tracking progress.

---

## Phase 2: Analysis

For each conflicted file, retrieve all three versions (common ancestor, ours & theirs) to understand what changed.

### Commands

```bash
# Common ancestor (stage 1) - the version before either branch diverged
git show :1:path/to/file

# Ours (stage 2) - current branch version (the branch you're merging INTO)
git show :2:path/to/file

# Theirs (stage 3) - incoming branch version (the branch being merged)
git show :3:path/to/file

# View the conflict markers in the working copy
cat path/to/file
```

### Understanding the Versions

| Stage | Description | Mnemonic |
|-------|-------------|----------|
| `:1:` | Common ancestor | "Before" |
| `:2:` | Ours (current branch) | "Mine" |
| `:3:` | Theirs (incoming branch) | "Yours" |

### Output

For each file, document:

- What changed in "ours" compared to the ancestor
- What changed in "theirs" compared to the ancestor
- Whether the changes overlap or are in different sections

---

## Phase 3: Context Gathering

Understand the intent behind each change to make informed resolution decisions.

### Commands

```bash
# View commits that touched this file on our branch (since diverging from the base branch)
git log --oneline <base-branch>..<our-branch> -- path/to/file

# View commits that touched this file on their branch (incoming branch)
git log --oneline <base-branch>..<their-branch> -- path/to/file

# View detailed commit messages for our changes
git log -p <base-branch>..<our-branch> -- path/to/file

# View detailed commit messages for their changes
git log -p <base-branch>..<their-branch> -- path/to/file
```

### Additional Context Sources

**Retrieve context using GitHub CLI:**

```bash
# Get PR details (if resolving conflicts during a PR)
gh pr view --json title,body,url 2>/dev/null || echo "No PR found for this branch"

# Search for linked GitHub issues by keyword
gh issue list --search "<keyword from branch or PR title>"

# View a specific GitHub issue
gh issue view <NNN>
```

- **PR descriptions**: Use `gh pr view` to retrieve PR context including description and linked issues
- **GitHub issues**: Use `gh issue view <NNN>` to read the issue explaining the feature/fix intent
- **Related files**: Check which files changed in the PR: `gh pr diff --name-only`
- **Documentation changes**: Look for README or doc updates explaining the change

### Output

For each conflicted file, document:

- The purpose of "our" changes
- The purpose of "their" changes
- Whether both changes are needed, or one supersedes the other

---

## Phase 4: Resolution

Apply file-type-specific strategies to resolve conflicts correctly.

### JSON Files (e.g., `cspell.json`, `package.json`)

**Key considerations:**

- **Preserve alphabetization**: Many JSON arrays (like `cspell.json` words) must remain sorted
- **Handle duplicate keys**: JSON doesn't allow duplicate keys; merge values appropriately
- **Validate syntax**: Ensure proper commas, brackets, and quotes after resolution

**Strategy:**

1. Identify which entries are new in each branch
2. Merge all unique entries
3. Re-sort arrays that require alphabetization
4. Remove any duplicates
5. Validate JSON syntax with a parser or linter

```bash
# Validate JSON after resolution (dependency-free)
python -m json.tool path/to/file.json >/dev/null 2>&1 || echo "JSON INVALID"
# Or use jq to format and validate (if available)
jq . path/to/file.json
```

### Markdown Files (e.g., `README.md`, documentation)

**Key considerations:**

- **Maintain heading numbering**: Numbered sections (1., 2., 3.) must remain sequential
- **Preserve section ordering**: Don't accidentally reorder major sections
- **Verify link validity**: Ensure internal links still point to valid anchors

**Strategy:**

1. Identify which sections were added/modified in each branch
2. Merge content preserving document flow
3. Renumber any numbered lists or sections
4. Verify all internal links resolve correctly

### Code Files (`.ts`, `.cs`, `.py`, etc.)

**Key considerations:**

- **Preserve both logical changes**: Both branches likely added needed functionality
- **Avoid duplication**: Don't include the same logic twice
- **Maintain existing style**: Follow the file's existing code patterns

**Strategy:**

1. Identify what each branch added/changed
2. Determine if changes are independent (can coexist) or overlapping (need merge)
3. For independent changes: include both
4. For overlapping changes: combine logic to achieve both intents
5. Ensure imports/dependencies are included for all merged code

```bash
# After resolving all conflicts, finalise and push.
#
# IMPORTANT: Check whether MERGE_HEAD exists — if so, you are completing a merge commit
# and must NOT use agdt-git-save-work (it amends, which would discard the merge parents).
#
# Case A — completing a merge commit (MERGE_HEAD exists):
git merge --continue        # finalise the merge commit (opens editor; use --no-edit to skip)
# or equivalently: git commit --no-edit
agdt-git-push               # push the true merge commit; the pre-push hook runs targeted checks
agdt-task-wait

# Case B — regular (non-merge) commit (MERGE_HEAD does not exist):
# agdt-git-save-work handles staging, commit/amend, and push in one step.
agdt-git-save-work
agdt-task-wait
```

### Configuration Files (`.yaml`, `.tf`, `.json` config)

**Key considerations:**

- **Merge settings additively**: When possible, include configuration from both branches
- **Watch for conflicting values**: Same key with different values needs human decision
- **Preserve structure**: Maintain proper indentation and formatting

**Strategy:**

1. Identify which settings were added/changed in each branch
2. For new, non-overlapping settings: include both
3. For conflicting values: determine correct value based on context
4. Flag settings requiring human decision with a TODO comment if uncertain

### Navigation Index Files (tables, lists)

**Key considerations:**

- **Maintain sort order**: Tables are often alphabetically sorted
- **Preserve column alignment**: Keep markdown table formatting clean
- **Include all entries**: Both branches may have added new rows

**Strategy:**

1. Extract all unique entries from both versions
2. Merge into a single list
3. Re-sort according to the file's ordering convention
4. Realign table columns if needed

---

## Phase 5: Verification

Before marking the conflict as resolved, verify completeness and correctness.

### Verification Checklist

For each resolved file, confirm:

- [ ] **No content from main branch lost** - All changes from the target branch are preserved
- [ ] **No content from feature branch lost** - All changes from the source branch are preserved
- [ ] **No duplicate content introduced** - Merged changes don't repeat logic/data
- [ ] **File-specific ordering/formatting correct**:
  - JSON arrays sorted if required (e.g., cspell.json words)
  - Markdown numbering sequential
  - Table rows properly ordered
- [ ] **All conflict markers removed** - No `<<<<<<<`, `=======`, or `>>>>>>>` remain
- [ ] **File is syntactically valid**:
  - JSON parses correctly
  - Code compiles without errors
  - YAML/config validates

### Verification Commands

```bash
# Ensure no conflict markers remain
grep -e '^<<<<<<< ' -e '^=======$' -e '^>>>>>>> ' path/to/file

# For JSON files - validate syntax (dependency-free)
python -m json.tool path/to/file.json >/dev/null 2>&1 || echo "JSON INVALID"

# Mark file as resolved
git add path/to/file
```

### Final Review

After resolving all files:

```bash
# Verify no conflicts remain
git diff --name-only --diff-filter=U

# Review all changes before completing merge
git diff --cached

# Complete the merge (only if all conflicts resolved)
# IMPORTANT: Do NOT use agdt-git-save-work here — it amends and would discard merge parents.
# Use git merge --continue (or git commit) to create the true merge commit, then push.
git merge --continue    # finalise merge commit (opens editor); or: git commit --no-edit
agdt-git-push           # push the true merge commit; the pre-push hook runs targeted checks
agdt-task-wait
```

---

## Edge Cases and Special Considerations

### Binary Files

Binary files (images, compiled assets) cannot be merged textually.

**Options:**

1. Keep ours: `git checkout --ours path/to/binary`
2. Keep theirs: `git checkout --theirs path/to/binary`
3. Use a specific version: `git checkout <commit-sha> -- path/to/binary`

**Guideline:** Review which version is correct based on PR context, or regenerate the file if it's a build artifact.

### Large Conflicts

For files with extensive conflicts exceeding AI context limits:

**Strategy:**

1. Resolve file-by-file rather than all at once
2. For large files, resolve section-by-section
3. Use diff tools to visualize changes: `git mergetool`
4. Consider breaking the merge into smaller, sequential merges

### Semantic Conflicts

Sometimes code merges cleanly but produces incorrect behavior (no markers, but incompatible logic).

**Detection:**

The pre-push hook runs targeted checks when you push, but it only runs tests when it detects
changed Python sources/tests. If you suspect semantic conflicts before pushing, review runtime
behavior and consider running relevant tests locally (optional) before pushing.

**Guideline:** Always push after completing a merge — the pre-push hook runs targeted checks for the changed files and can catch many merge regressions early.

### Auto-Generated Files

Some files should be regenerated rather than manually merged:

| File Type | Action |
|-----------|--------|
| `agentic_devtools/_version.py` | **Never edit or commit** — auto-generated by `hatch-vcs` from Git tags |
| Build artifacts (`*.egg-info`, `dist/`) | Rebuild the project |

`_version.py` is gitignored and should never appear in merge conflicts. If it does, remove it so it stays untracked and is regenerated:

```bash
# Remove from working tree (if present)
rm -f agentic_devtools/_version.py
# Ensure it is not tracked or staged in git
git rm --cached agentic_devtools/_version.py 2>/dev/null || true
```

---

## Conflict Resolution Summary Template

After completing all resolutions, document your work:

```markdown
## Merge Conflict Resolution Summary

**Source branch:** `<branch-name>`
**Target branch:** main
**Total conflicts:** X files

### Resolved Files

| File | Resolution Strategy | Notes |
|------|---------------------|-------|
| path/to/file1 | Merged both changes | Independent additions |
| path/to/file2 | Kept theirs | Our change was reverted intentionally |
| cspell.json | Merged + re-sorted | Combined word lists alphabetically |

### Verification

- [ ] Push succeeds (pre-push hook completes and any targeted checks for the changed files pass)
- [ ] No conflict markers remain
- [ ] Reviewed diff of all resolved files
```
