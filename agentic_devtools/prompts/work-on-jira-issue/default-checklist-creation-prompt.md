# Work on Jira Issue - Checklist Creation Step

You are creating an implementation checklist for Jira issue **{{issue_key}}**: {{issue_summary}}

## Your Task

Create a detailed checklist of specific, actionable items that need to be completed for this issue. The checklist will guide the implementation step and track progress.

## Guidelines for Checklist Items

1. **Be specific** - Each item should describe a concrete, verifiable task
2. **Match acceptance criteria** - Ensure each AC from the issue is represented
3. **Add technical tasks** - Include necessary code, test, and documentation work
4. **Keep items small** - Each item should be completable in a focused session
5. **Order logically** - Dependencies should come before dependent items

## Example Checklist Items

Good checklist items:

- "Add `DataproductCommands.UpdateDescription()` method in Application layer"
- "Create unit test for description update validation"
- "Update README.md with new API endpoint documentation"
- "Add migration for new `Description` column"

Poor checklist items (too vague):

- "Implement the feature"
- "Write tests"
- "Update docs"

## Creating the Checklist

Use the following command to create your checklist:

```bash
dfly-create-checklist "1. First task|2. Second task|3. Third task"
```

Or use the multi-line format for better readability:

```bash
dfly-set checklist_items "1. First specific task to complete
2. Second specific task to complete
3. Add unit tests for new functionality
4. Update relevant documentation"
dfly-create-checklist
```

## Important Notes

- The checklist can be modified during implementation if needed
- Each item will be tracked and marked complete as you progress
- When all items are complete and code is committed, a review sub-step will trigger

---

**Workflow Status**: Checklist creation in progress. After creating the checklist, the workflow will advance to implementation.
