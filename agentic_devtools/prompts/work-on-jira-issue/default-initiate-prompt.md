# Work on Jira Issue Workflow

You are working on Jira issue **{{jira_issue_key}}**.

## Getting Started

1. Retrieve the full issue details:

   ```bash
   dfly-set jira.issue_key {{jira_issue_key}}
   dfly-get-jira-issue
   ```

2. Review the issue details for:
   - **Summary**: What needs to be accomplished
   - **Description**: User story and detailed context
   - **Acceptance Criteria**: Specific requirements to meet
   - **Comments**: Additional context and discussions

## Planning Phase

1. Break down the issue into manageable tasks using the todo list tool
2. Identify affected components and files
3. Post your implementation plan to Jira:

   ```bash
   dfly-set jira.comment "h4. Implementation Plan\n\n*Scope:*\n* <goal>\n\n*Tasks:*\n* 1) <task 1>\n* 2) <task 2>"
   dfly-add-jira-comment
   ```

## Implementation Phase

1. Create a feature branch:

   ```bash
   git switch -c feature/{{jira_issue_key}}/short-description
   ```

2. Implement changes following repository conventions
3. Add/update tests for all logic changes
4. Update documentation as needed

## Completion Phase

1. Commit your changes:

   ```bash
   dfly-set commit_message "feature([{{jira_issue_key}}](https://jira.swica.ch/browse/{{jira_issue_key}})): <summary>\n\n- <change 1>\n- <change 2>\n\n[{{jira_issue_key}}](https://jira.swica.ch/browse/{{jira_issue_key}})"
   dfly-git-commit
   ```

2. Create a pull request:

   ```bash
   dfly-create-pull-request
   ```

3. Post completion comment to Jira

## Quality Gates

Before completing, ensure:

- [ ] Build succeeds without warnings
- [ ] All tests pass
- [ ] No new analyzer warnings
- [ ] Documentation updated if needed
