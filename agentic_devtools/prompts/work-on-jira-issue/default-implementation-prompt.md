# Work on Jira Issue - Implementation Step

You are implementing Jira issue **{{issue_key}}**: {{issue_summary}}

## Implementation Checklist

{{checklist_markdown}}

## Your Task

Work through the checklist items above. For each item:

1. **Implement the change** - Follow existing patterns and conventions
2. **Test your work** - Verify the item is truly complete
3. **Mark it complete** - Use the `--completed` flag when committing

## Key Guidelines

- **Single commit per issue** - All work goes into one commit (use amend for

  updates)
  updates)

- **Follow existing patterns** - Match the codebase style and conventions
- **Add/update tests** - Ensure test coverage for new code
- **Update documentation** - Keep README and instruction files current
- **Use `agdt-test` for testing** - Never run `pytest` directly (see Running Tests below)

## Running Tests

Always use `agdt-test` commands — never run `pytest` directly:

```bash
# Quick check (no coverage) — background task
agdt-test-quick
agdt-task-wait

# Full suite with coverage — background task
agdt-test
agdt-task-wait

# Specific test file or pattern — synchronous
agdt-test-pattern tests/unit/cli/git/core/test_get_current_branch.py -v
```

## Committing Your Work

When you complete one or more checklist items, commit with the `--completed`
flag:

```bash
agdt-git-commit --completed "1,2,3"
```

The command:

- Automatically detects whether to create a new commit or amend
- Marks the specified checklist items as complete
- Auto-triggers implementation review when all items are done

## Modifying the Checklist

If you need to add, remove, or modify checklist items:

```bash
# Add a new item
agdt-update-checklist --add "New task discovered during implementation"

# Remove an item (by ID)
agdt-update-checklist --remove "5"

# Mark items complete without committing
agdt-update-checklist --complete "1,2"

# Revert items to incomplete
agdt-update-checklist --revert "3"
```

## Repository Conventions

Follow the conventions documented in:

- `.github/copilot-instructions.md` (root and local)
- `docs/code-change-guidance.md`
- `docs/codebase-conventions.md`

---

**Workflow Status**: Implementation in progress. Complete all checklist items
and commit to trigger implementation review.
