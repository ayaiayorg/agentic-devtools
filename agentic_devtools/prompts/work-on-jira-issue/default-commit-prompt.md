# Work on Jira Issue - Commit Step

You are preparing to commit work for Jira issue **{{issue_key}}**: {{issue_summary}}

## Your Task

Create a well-formatted commit with all your changes.

## Commit Message Format

Use this format for your commit message:

```none
feature([{{issue_key}}](https://jira.swica.ch/browse/{{issue_key}})): <short summary>

- <change 1>
- <change 2>
- <change 3>

[{{issue_key}}](https://jira.swica.ch/browse/{{issue_key}})
```

## Pre-Commit Checklist

- [ ] All changes are staged (`git add -A`)
- [ ] Commit message follows the format above
- [ ] No unrelated changes included
- [ ] Branch name contains the issue key

## Next Action

Set your commit message and create the commit:

```bash
dfly-set commit_message "feature([{{issue_key}}](https://jira.swica.ch/browse/{{issue_key}})): <summary>

- <change 1>
- <change 2>

[{{issue_key}}](https://jira.swica.ch/browse/{{issue_key}})"

dfly-git-save-work
```

---

**Workflow Status**: Commit step. After committing, the workflow will advance to the pull-request step.
