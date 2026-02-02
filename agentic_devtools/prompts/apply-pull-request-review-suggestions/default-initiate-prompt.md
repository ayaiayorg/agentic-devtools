# Apply Pull Request Review Suggestions Workflow

You are applying review suggestions from Pull Request #{{pull_request_id}}.

## Getting Started

1. Retrieve the pull request details and review comments:

   ```bash
   agdt-set pull_request_id {{pull_request_id}}
   agdt-get-pull-request
   ```

2. Review all feedback and suggestions provided by reviewers

## Categorizing Feedback

Organize the suggestions into:

### Must Fix

- Security issues
- Bug fixes
- Breaking changes
- Failing tests

### Should Fix

- Code quality improvements
- Performance optimizations
- Documentation updates

### Consider

- Style preferences
- Alternative approaches
- Nice-to-have improvements

## Applying Changes

1. Address each suggestion systematically:

   - Work through "Must Fix" items first
   - Then "Should Fix" items
   - Evaluate "Consider" items

2. For each change:
   - Make the modification
   - Verify it works as expected
   - Consider adding tests if applicable

## Responding to Reviewers

For each addressed comment:

- Resolve the conversation in the PR
- Or reply with context if you chose a different approach

## Updating the PR

1. Stage and amend your commit (agdt-git-commit auto-detects amend):

   ```bash
   agdt-git-commit
   ```

2. If new issues were found during review, update the Jira issue:

   ```bash
   agdt-set jira.issue_key {{jira_issue_key}}
   agdt-set jira.comment "h4. Addressed Review Feedback\n\n*Changes Made:*\n* <change 1>\n* <change 2>"
   agdt-add-jira-comment
   ```

## Quality Verification

Before requesting re-review:

- [ ] All tests pass
- [ ] Build succeeds
- [ ] All "Must Fix" items addressed
- [ ] Reviewers' concerns answered
