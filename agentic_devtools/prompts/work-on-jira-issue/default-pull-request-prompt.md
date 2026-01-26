# Work on Jira Issue - Pull Request Step

You are creating a pull request for Jira issue **{{issue_key}}**: {{issue_summary}}

## Your Task

Create a draft pull request for your changes.

## PR Details

- **Source Branch**: {{branch_name}}
- **Target Branch**: main
- **Draft Mode**: Yes (PR will be created as draft)

## PR Title Format

```none
feature([{{issue_key}}](https://jira.swica.ch/browse/{{issue_key}})): <short summary>
```

## PR Description Template

```markdown
Implements {{issue_key}}: {{issue_summary}}

## Summary

- <high-level description of changes>

## Changes

- `path/to/file1` - <what changed>
- `path/to/file2` - <what changed>

## Testing

- [ ] Unit tests added/updated
- [ ] Manual testing completed

[{{issue_key}}](https://jira.swica.ch/browse/{{issue_key}})
```

## Next Action

Set PR details and create the pull request:

```bash
dfly-set source_branch '{{branch_name}}'
dfly-set title 'feature([{{issue_key}}](https://jira.swica.ch/browse/{{issue_key}})): <summary>'
dfly-set description '<PR description>'
dfly-create-pull-request
```

---

**Workflow Status**: Pull request step. After creating the PR, the workflow will advance to the completion step.
