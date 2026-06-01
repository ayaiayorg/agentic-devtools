# Managed Prompt Skills

> **This folder is managed by [agentic-devtools](https://github.com/ayaiayorg/agentic-devtools).**
> Do **not** edit these files manually — they are overwritten by `agdt-setup`.

The files below are mirrored from the `agentic-devtools` package so that
Copilot CLI and similar tools can discover and use them by convention.
They should be checked into source control like any other `.github`
configuration, and any local edits will be overwritten the next time
`agdt-setup` is run.

## File Manifest

| File | Description |
| ---- | ----------- |
| `agdt.add-jira-comment.prompt.md` | agdt.add-jira-comment |
| `agdt.add-pull-request-comment.prompt.md` | agdt.add-pull-request-comment |
| `agdt.add-users-to-project-role-batch.prompt.md` | agdt.add-users-to-project-role-batch |
| `agdt.add-users-to-project-role.prompt.md` | agdt.add-users-to-project-role |
| `agdt.address-copilot-review.ci-repair.prompt.md` | Address Copilot PR Review Comments (CI Repair Mode) |
| `agdt.address-copilot-review.evaluate-and-respond.prompt.md` | Address Copilot PR Review Comments — Evaluate and Respond |
| `agdt.address-copilot-review.prompt.md` | Address Copilot PR Review Comments |
| `agdt.advance-workflow.prompt.md` | agdt.advance-workflow |
| `agdt.analyze-workflow.prompt.md` | Workflow Analysis Agent |
| `agdt.apply-pr-suggestions.initiate.prompt.md` | agdt.apply-pr-suggestions.initiate |
| `agdt.approve-file.prompt.md` | agdt.approve-file |
| `agdt.approve-pull-request.prompt.md` | agdt.approve-pull-request |
| `agdt.autonomous-issue-refinement.prompt.md` | agdt.autonomous-issue-refinement |
| `agdt.azure-context-current.prompt.md` | agdt.azure-context-current |
| `agdt.azure-context-ensure-login.prompt.md` | agdt.azure-context-ensure-login |
| `agdt.azure-context-status.prompt.md` | agdt.azure-context-status |
| `agdt.azure-context-use.prompt.md` | agdt.azure-context-use |
| `agdt.break-down-issue-into-subtasks.initiate.prompt.md` | agdt.break-down-issue-into-subtasks.initiate |
| `agdt.check-user-exists.prompt.md` | agdt.check-user-exists |
| `agdt.check-users-exist.prompt.md` | agdt.check-users-exist |
| `agdt.clear-workflow.prompt.md` | agdt.clear-workflow |
| `agdt.clear.prompt.md` | agdt.clear |
| `agdt.confirm-suggestion-addressed.prompt.md` | agdt.confirm-suggestion-addressed |
| `agdt.copilot-auto-start.prompt.md` | agdt.copilot-auto-start |
| `agdt.create-agdt-bug-issue.prompt.md` | agdt.create-agdt-bug-issue |
| `agdt.create-agdt-documentation-issue.prompt.md` | agdt.create-agdt-documentation-issue |
| `agdt.create-agdt-feature-issue.prompt.md` | agdt.create-agdt-feature-issue |
| `agdt.create-agdt-issue.prompt.md` | agdt.create-agdt-issue |
| `agdt.create-agdt-task-issue.prompt.md` | agdt.create-agdt-task-issue |
| `agdt.create-checklist.prompt.md` | agdt.create-checklist |
| `agdt.create-epic.prompt.md` | agdt.create-epic |
| `agdt.create-issue.prompt.md` | agdt.create-issue |
| `agdt.create-issues-from-analysis.prompt.md` | agdt.create-issues-from-analysis |
| `agdt.create-jira-epic.initiate.prompt.md` | agdt.create-jira-epic.initiate |
| `agdt.create-jira-issue.initiate.prompt.md` | agdt.create-jira-issue.initiate |
| `agdt.create-jira-subtask.initiate.prompt.md` | agdt.create-jira-subtask.initiate |
| `agdt.create-pipeline.prompt.md` | agdt.create-pipeline |
| `agdt.create-pull-request.prompt.md` | agdt.create-pull-request |
| `agdt.create-subtask.prompt.md` | agdt.create-subtask |
| `agdt.delete.prompt.md` | agdt.delete |
| `agdt.find-role-id-by-name.prompt.md` | agdt.find-role-id-by-name |
| `agdt.get-jira-issue.prompt.md` | agdt.get-jira-issue |
| `agdt.get-next-workflow-prompt.prompt.md` | agdt.get-next-workflow-prompt |
| `agdt.get-pipeline-id.prompt.md` | agdt.get-pipeline-id |
| `agdt.get-project-role-details.prompt.md` | agdt.get-project-role-details |
| `agdt.get-pull-request-details.prompt.md` | agdt.get-pull-request-details |
| `agdt.get-pull-request-threads.prompt.md` | agdt.get-pull-request-threads |
| `agdt.get-run-details.prompt.md` | agdt.get-run-details |
| `agdt.get-workflow.prompt.md` | agdt.get-workflow |
| `agdt.get.prompt.md` | agdt.get |
| `agdt.git-force-push.prompt.md` | agdt.git-force-push |
| `agdt.git-publish.prompt.md` | agdt.git-publish |
| `agdt.git-push.prompt.md` | agdt.git-push |
| `agdt.git-save-work.prompt.md` | agdt.git-save-work |
| `agdt.git-stage.prompt.md` | agdt.git-stage |
| `agdt.git-sync.prompt.md` | agdt.git-sync |
| `agdt.list-pipelines.prompt.md` | agdt.list-pipelines |
| `agdt.list-project-roles.prompt.md` | agdt.list-project-roles |
| `agdt.mark-file-reviewed.prompt.md` | agdt.mark-file-reviewed |
| `agdt.mark-pull-request-draft.prompt.md` | agdt.mark-pull-request-draft |
| `agdt.network-status.prompt.md` | agdt.network-status |
| `agdt.optimize-issue-for-ai-agent.initiate.prompt.md` | agdt.optimize-issue-for-ai-agent.initiate |
| `agdt.parse-jira-error-report.prompt.md` | agdt.parse-jira-error-report |
| `agdt.pr-merge-manager.prompt.md` | PR Merge Manager |
| `agdt.publish-pull-request.prompt.md` | agdt.publish-pull-request |
| `agdt.pull-request-review.completion.prompt.md` | agdt.pull-request-review.completion |
| `agdt.pull-request-review.decision.prompt.md` | agdt.pull-request-review.decision |
| `agdt.pull-request-review.file-review.prompt.md` | agdt.pull-request-review.file-review |
| `agdt.pull-request-review.initiate.prompt.md` | agdt.pull-request-review.initiate |
| `agdt.query-app-insights.prompt.md` | agdt.query-app-insights |
| `agdt.query-fabric-dap-errors.prompt.md` | agdt.query-fabric-dap-errors |
| `agdt.query-fabric-dap-provisioning.prompt.md` | agdt.query-fabric-dap-provisioning |
| `agdt.query-fabric-dap-timeline.prompt.md` | agdt.query-fabric-dap-timeline |
| `agdt.reject-suggestion-resolution.prompt.md` | agdt.reject-suggestion-resolution |
| `agdt.release-pypi.prompt.md` | agdt.release-pypi |
| `agdt.reply-to-pull-request-thread.prompt.md` | agdt.reply-to-pull-request-thread |
| `agdt.request-changes-with-suggestion.prompt.md` | agdt.request-changes-with-suggestion |
| `agdt.request-changes.prompt.md` | agdt.request-changes |
| `agdt.resolve-merge-conflicts.prompt.md` | Resolve Merge Conflicts |
| `agdt.resolve-thread.prompt.md` | agdt.resolve-thread |
| `agdt.review.prompt.md` | agdt.review |
| `agdt.run-e2e-tests-fabric.prompt.md` | agdt.run-e2e-tests-fabric |
| `agdt.run-e2e-tests-synapse.prompt.md` | agdt.run-e2e-tests-synapse |
| `agdt.run-wb-patch.prompt.md` | agdt.run-wb-patch |
| `agdt.set.prompt.md` | agdt.set |
| `agdt.setup-certs.prompt.md` | agdt.setup-certs |
| `agdt.setup-check.prompt.md` | agdt.setup-check |
| `agdt.setup-copilot-cli.prompt.md` | agdt.setup-copilot-cli |
| `agdt.setup-gh-cli.prompt.md` | agdt.setup-gh-cli |
| `agdt.setup-worktree-background.prompt.md` | agdt.setup-worktree-background |
| `agdt.setup.prompt.md` | agdt.setup |
| `agdt.show-checklist.prompt.md` | agdt.show-checklist |
| `agdt.show-other-incomplete-tasks.prompt.md` | agdt.show-other-incomplete-tasks |
| `agdt.show.prompt.md` | agdt.show |
| `agdt.squash-commits.prompt.md` | Squash Commits |
| `agdt.submit-file-review.prompt.md` | agdt.submit-file-review |
| `agdt.task-log.prompt.md` | agdt.task-log |
| `agdt.task-status.prompt.md` | agdt.task-status |
| `agdt.task-wait.prompt.md` | agdt.task-wait |
| `agdt.tasks-clean.prompt.md` | agdt.tasks-clean |
| `agdt.tasks.prompt.md` | agdt.tasks |
| `agdt.test-file.prompt.md` | agdt.test-file |
| `agdt.test-pattern.prompt.md` | agdt.test-pattern |
| `agdt.test-quick.prompt.md` | agdt.test-quick |
| `agdt.test.prompt.md` | agdt.test |
| `agdt.update-checklist.prompt.md` | agdt.update-checklist |
| `agdt.update-jira-issue.initiate.prompt.md` | agdt.update-jira-issue.initiate |
| `agdt.update-jira-issue.prompt.md` | agdt.update-jira-issue |
| `agdt.update-pipeline.prompt.md` | agdt.update-pipeline |
| `agdt.vpn-off.prompt.md` | agdt.vpn-off |
| `agdt.vpn-on.prompt.md` | agdt.vpn-on |
| `agdt.vpn-run.prompt.md` | agdt.vpn-run |
| `agdt.vpn-status.prompt.md` | agdt.vpn-status |
| `agdt.wait-for-run.prompt.md` | agdt.wait-for-run |
| `agdt.work-on-jira-issue.checklist-creation.prompt.md` | agdt.work-on-jira-issue.checklist-creation |
| `agdt.work-on-jira-issue.commit.prompt.md` | agdt.work-on-jira-issue.commit |
| `agdt.work-on-jira-issue.completion.prompt.md` | agdt.work-on-jira-issue.completion |
| `agdt.work-on-jira-issue.implementation-review.prompt.md` | agdt.work-on-jira-issue.implementation-review |
| `agdt.work-on-jira-issue.implementation.prompt.md` | agdt.work-on-jira-issue.implementation |
| `agdt.work-on-jira-issue.initiate.prompt.md` | agdt.work-on-jira-issue.initiate |
| `agdt.work-on-jira-issue.planning.prompt.md` | agdt.work-on-jira-issue.planning |
| `agdt.work-on-jira-issue.pull-request.prompt.md` | agdt.work-on-jira-issue.pull-request |
| `agdt.work-on-jira-issue.retrieve.prompt.md` | agdt.work-on-jira-issue.retrieve |
| `agdt.work-on-jira-issue.setup.prompt.md` | agdt.work-on-jira-issue.setup |
| `agdt.work-on-jira-issue.verification.prompt.md` | agdt.work-on-jira-issue.verification |

## Regeneration

Run `agdt-setup` to update these files.  Stale files (removed in newer
package versions) are automatically cleaned up.
