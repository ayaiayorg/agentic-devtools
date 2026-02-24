# Work on Jira Issue - Implementation Step

You are implementing Jira issue **{{issue_key}}**: {{issue_summary}}

## Implementation Checklist

{{checklist_markdown}}

## Your Task

Work through the checklist items above using the **TDD red-green-refactor cycle**.
For each item:

1. **Write a failing test FIRST (RED)** — create the test file before any source changes
2. **Confirm the test fails** — run it to verify it is actually testing new behaviour
3. **Write minimal implementation (GREEN)** — add only what is needed to pass the test
4. **Confirm the test passes** — run it again to verify
5. **Refactor if needed (REFACTOR)** — improve code quality while keeping tests green
6. **Check coverage** — ensure the source file maintains 100% coverage
7. **Mark it complete** — use the `--completed` flag when committing

### TDD Commands

```bash
# Step 1 & 2: confirm test fails (RED)
agdt-test-pattern tests/unit/<path>/test_<symbol>.py -v

# Step 3 & 4: confirm test passes after implementation (GREEN)
agdt-test-pattern tests/unit/<path>/test_<symbol>.py -v

# Step 6: re-run all tests for the source file's test suite (REFACTOR)
# NOTE: use agdt-test-pattern, NOT agdt-test-file — agdt-test-file only supports
# legacy flat test files (tests/test_<module>.py) and will fail for 1:1:1 tests
agdt-test-pattern tests/unit/<path>/ -v

# After ALL checklist items are complete: run full suite
agdt-test
agdt-task-wait
```

## Key Guidelines

- **Write tests before source code** — no exceptions
- **Single commit per issue** - All work goes into one commit (use amend for updates)

- **Follow existing patterns** - Match the codebase style and conventions
- **100% test coverage required** - Every new line of code must be covered
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
