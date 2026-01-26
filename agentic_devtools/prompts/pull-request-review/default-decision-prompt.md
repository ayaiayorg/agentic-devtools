# Pull Request Review - Decision Step

You have completed reviewing Pull Request **#{{pull_request_id}}**.

## Review Summary

- **Files Reviewed**: {{completed_count}}
- **Approvals**: {{approval_count}}
- **Change Requests**: {{changes_count}}

## Your Task

Make a final decision on the PR:

### If Approving

The PR meets quality standards and can be merged:

```bash
dfly-set content "PR approved. All changes meet quality standards and follow repository conventions."
dfly-set is_pull_request_approval true
dfly-add-pull-request-comment
dfly-task-wait
```

### If Requesting Changes

The PR requires modifications before it can be merged:

```bash
dfly-set content "Changes requested. Please address the review comments before this PR can be approved:

1. [Critical issue 1]
2. [Critical issue 2]

Once addressed, re-request review."
dfly-add-pull-request-comment
dfly-task-wait
```

## Decision Guidelines

**Approve if:**

- All critical issues have been addressed
- Code follows repository conventions
- Tests are adequate
- Documentation is complete

**Request changes if:**

- Security vulnerabilities exist
- Critical bugs are present
- Required tests are missing
- Breaking changes are not documented

## After Decision

The workflow will automatically advance to completion.

---

**Workflow Status**: Ready for final decision.
