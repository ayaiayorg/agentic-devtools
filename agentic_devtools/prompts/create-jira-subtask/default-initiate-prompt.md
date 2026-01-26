# Create Jira Subtask Workflow

You are creating a subtask under parent issue **{{jira_parent_key}}**.

## Understanding Subtasks

Subtasks are smaller pieces of work that:

- Break down a larger story or task
- Are tracked within the parent issue
- Help with progress visibility and assignment

## Gathering Information

Before creating the subtask:

1. Review the parent issue to understand the context
2. Define a clear, actionable scope for the subtask
3. Ensure the subtask is small enough to complete in one session

## Creating the Subtask

1. Set the required state:

   ```bash
   dfly-set jira.parent_key {{jira_parent_key}}
   dfly-set jira.summary "<subtask summary>"
   dfly-set jira.description "<detailed description>"
   ```

2. Create the subtask:

   ```bash
   dfly-create-subtask
   ```

## Best Practices

### Good Subtask Examples

- "Add unit tests for UserService.Create method"
- "Update API documentation for new endpoint"
- "Implement validation logic for email field"

### Avoid

- Subtasks that are too large (should be their own story)
- Vague descriptions like "Fix stuff" or "Misc work"
- Duplicate subtasks

## After Creation

The command outputs the new subtask key. Consider:

- Assigning the subtask appropriately
- Setting time estimates if required
- Linking related subtasks or issues
