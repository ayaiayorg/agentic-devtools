# Pull Request Review - Summary Step

All files in Pull Request **#{{pull_request_id}}** have been reviewed.

## Review Statistics

- **Files Reviewed**: {{completed_count}}
- **Approvals**: {{approval_count}}
- **Change Requests**: {{changes_count}}

## Your Task

The PR summary is being generated automatically in the background. The workflow
auto-started the summary task when all file reviews completed.

The summary:

1. **Groups findings by folder/area** for easy navigation
2. **Highlights critical issues** that must be addressed
3. **Notes positive aspects** and good patterns observed
4. **Provides actionable recommendations**

## Next Action

Wait for the summary background task to complete:

```bash
agdt-task-wait
```

This will wait for the summary to finish and then auto-advance the workflow to
the next step.

---

**Workflow Status**: File reviews complete. Summary generation in progress.
