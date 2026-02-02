# Pull Request Review - Summary Step

All files in Pull Request **#{{pull_request_id}}** have been reviewed.

## Review Statistics

- **Files Reviewed**: {{completed_count}}
- **Approvals**: {{approval_count}}
- **Change Requests**: {{changes_count}}

## Your Task

Generate folder-by-folder summary comments for the PR.

The summary should:

1. **Group findings by folder/area** for easy navigation
2. **Highlight critical issues** that must be addressed
3. **Note positive aspects** and good patterns observed
4. **Provide actionable recommendations**

## Next Action

Generate the PR summary:

```bash
agdt-generate-pr-summary
agdt-task-wait
```

This will:

- Analyze all file reviews
- Generate grouped summary comments
- Post them to the PR
- Auto-advance to the decision step

---

**Workflow Status**: File reviews complete. Ready to generate summary.
