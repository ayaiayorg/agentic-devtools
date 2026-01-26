# Pull Request Review - Complete

You have completed the review of Pull Request **#{{pull_request_id}}**.

## Summary

- **PR ID**: {{pull_request_id}}
  {% if jira_issue_key %}
- **Jira Issue**: [{{jira_issue_key}}](https://jira.swica.ch/browse/{{jira_issue_key}})
  {% endif %}
- **Files Reviewed**: {{completed_count}}
- **Decision**: {{decision}}

## Optional: Post Jira Comment

If linked to a Jira issue, post a summary comment:

```bash
dfly-set jira.comment "h4. PR Review Complete

*PR:* #{{pull_request_id}}
*Decision:* {{decision}}
*Files Reviewed:* {{completed_count}}

*Summary:*
* <key findings>

*Next Steps:*
* <what the author should do>"
dfly-add-jira-comment
```

## Workflow Complete

The pull request review workflow is now complete.

To clear the workflow state:

```bash
dfly-clear-workflow
```

---

**Workflow Status**: ✅ Complete
