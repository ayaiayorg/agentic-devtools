# Work on Jira Issue - Implementation Review Step

All checklist items for **{{issue_key}}** have been marked complete. Review your implementation before proceeding to verification.

## Current Status

{{checklist_markdown}}

## Review Checklist

Before advancing to verification, confirm:

### Code Quality

- [ ] All new code follows existing patterns and conventions
- [ ] No debugging code, console.log, or TODO comments left behind
- [ ] Error handling is appropriate and consistent
- [ ] Code is properly formatted (linting passes)

### Test Coverage

- [ ] Unit tests cover new functionality
- [ ] Edge cases and error conditions are tested
- [ ] Existing tests still pass

### Documentation

- [ ] README updates reflect new functionality (if applicable)
- [ ] Code comments explain non-obvious logic
- [ ] API documentation is current (if applicable)

### Acceptance Criteria

- [ ] All acceptance criteria from the issue are satisfied
- [ ] Implementation matches the planned approach

## Next Actions

If everything looks good, advance to verification:

```bash
dfly-advance-workflow verification
```

If you find issues to fix:

1. Make the necessary corrections
2. Update checklist if needed: `dfly-update-checklist --add "Fix discovered issue"`
3. Commit the fixes: `dfly-git-commit --completed "new_item_id"`
4. This review will re-trigger when complete

If you need to revert a checklist item to incomplete:

```bash
dfly-update-checklist --revert "1,2"
```

---

**Workflow Status**: Implementation review. All checklist items complete. Advance to verification when satisfied.
