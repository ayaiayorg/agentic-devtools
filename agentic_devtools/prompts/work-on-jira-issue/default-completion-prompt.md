# Work on Jira Issue - Completion Step

You have completed work on Jira issue **{{issue_key}}**: {{issue_summary}}

## Summary

- **Issue**: {{issue_key}}
- **Branch**: {{branch_name}}
- **PR ID**: {{pull_request_id}}
- **PR URL**: {{pull_request_url}}

## Your Task

Post a completion comment to the Jira issue summarizing the work done.

## Completion Comment Format

```none
h4. Work Complete

*Summary:*
* <what was accomplished>

*PR:* #{{pull_request_id}}
*Branch:* {{{{branch_name}}}}

*Quality Gates:*
* Build: ✅
* Tests: ✅ <count> passing
* Style: ✅

Ready for review and merge.
```

## Next Action

Post the completion comment:

```bash
agdt-set jira.comment "h4. Work Complete

*Summary:*
* <what was accomplished>

*PR:* #{{pull_request_id}}
*Branch:* {{{{branch_name}}}}

*Quality Gates:*
* Build: ✅
* Tests: ✅
* Style: ✅

Ready for review and merge."
agdt-add-jira-comment
```

---

**Workflow Status**: ✅ Complete! The workflow has finished successfully.

To clear the workflow state:

```bash
agdt-clear-workflow
```
