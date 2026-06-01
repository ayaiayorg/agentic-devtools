# Managed Agent Skills

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
| `agdt.add-jira-comment.agent.md` | Add Jira Comment: Add a comment to a Jira issue |
| `agdt.add-pull-request-comment.agent.md` | Add PR Comment: Post a comment on a pull request |
| `agdt.add-users-to-project-role-batch.agent.md` | Add Users to Role Batch: Batch add users to a role |
| `agdt.add-users-to-project-role.agent.md` | Add Users to Role: Add users to a Jira project role |
| `agdt.address-copilot-review.agent.md` | Address Copilot Review: Automatically address GitHub Copilot PR review comments by URL |
| `agdt.address-copilot-review.ci-repair.agent.md` | Address Copilot Review (CI Repair): Automatically address GitHub Copilot PR review comments and CI failures in a CI environment |
| `agdt.address-copilot-review.evaluate-and-respond.agent.md` | Address Copilot Review (Evaluate and Respond): Evaluate review comments, make targeted changes, and post a structured resolution summary |
| `agdt.advance-workflow.agent.md` | Advance Workflow: Advance to next workflow step |
| `agdt.analyze-workflow.agent.md` | Analyze Workflow: Perform deep code analysis with multi-identity log scanning, external worktree context, and parameterized scoping via --issue-key or --pr-id |
| `agdt.apply-pr-suggestions.initiate.agent.md` | Apply PR Suggestions - Initiate: Apply PR review suggestions |
| `agdt.approve-file.agent.md` | Approve File: Approve a file during PR review |
| `agdt.approve-pull-request.agent.md` | Approve PR: Approve a pull request with sentinel banner |
| `agdt.autonomous-issue-refinement.agent.md` | Autonomous Issue Refinement: Autonomously refine a GitHub or Jira issue into an implementation-ready specification without human intervention |
| `agdt.azure-context-current.agent.md` | Azure Context Current: Show current Azure context |
| `agdt.azure-context-ensure-login.agent.md` | Azure Context Login: Ensure Azure CLI is logged in |
| `agdt.azure-context-status.agent.md` | Azure Context Status: Show Azure context status |
| `agdt.azure-context-use.agent.md` | Azure Context Use: Switch Azure context |
| `agdt.break-down-issue-into-subtasks.initiate.agent.md` | Break Down Issue - Initiate: Break down a Jira issue into subtasks |
| `agdt.check-user-exists.agent.md` | Check User Exists: Check if a Jira user exists |
| `agdt.check-users-exist.agent.md` | Check Users Exist: Check if multiple Jira users exist |
| `agdt.clear-workflow.agent.md` | Clear Workflow: Clear the current workflow state |
| `agdt.clear.agent.md` | Clear State: Remove all values from the agdt state |
| `agdt.confirm-suggestion-addressed.agent.md` | Confirm Suggestion: Confirm a review suggestion was addressed |
| `agdt.copilot-auto-start.agent.md` | Copilot Auto-Start: Auto-start a Copilot session |
| `agdt.create-agdt-bug-issue.agent.md` | Create Bug Issue: Create a bug issue in agentic-devtools |
| `agdt.create-agdt-documentation-issue.agent.md` | Create Doc Issue: Create a documentation issue in agentic-devtools |
| `agdt.create-agdt-feature-issue.agent.md` | Create Feature Issue: Create a feature issue in agentic-devtools |
| `agdt.create-agdt-issue.agent.md` | Create GitHub Issue: Create an issue in agentic-devtools |
| `agdt.create-agdt-task-issue.agent.md` | Create Task Issue: Create a task issue in agentic-devtools |
| `agdt.create-checklist.agent.md` | Create Checklist: Create a workflow checklist |
| `agdt.create-epic.agent.md` | Create Epic: Create a new Jira epic |
| `agdt.create-issue.agent.md` | Create Issue: Create a new Jira issue |
| `agdt.create-issues-from-analysis.agent.md` | Create Issues from Analysis: Create GitHub issues in bulk from a structured workflow analysis JSON file |
| `agdt.create-jira-epic.initiate.agent.md` | Create Jira Epic - Initiate: Create a new Jira epic |
| `agdt.create-jira-issue.initiate.agent.md` | Create Jira Issue - Initiate: Create a new Jira issue |
| `agdt.create-jira-subtask.initiate.agent.md` | Create Jira Subtask - Initiate: Create a Jira subtask |
| `agdt.create-pipeline.agent.md` | Create Pipeline: Create an Azure DevOps pipeline |
| `agdt.create-pull-request.agent.md` | Create PR: Create a new pull request |
| `agdt.create-subtask.agent.md` | Create Subtask: Create a new Jira subtask |
| `agdt.delete.agent.md` | Delete State Value: Remove a key from the agdt state |
| `agdt.find-role-id-by-name.agent.md` | Find Role ID: Find a Jira role ID by name |
| `agdt.get-jira-issue.agent.md` | Get Jira Issue: Retrieve Jira issue details |
| `agdt.get-next-workflow-prompt.agent.md` | Get Next Prompt: Get the next workflow step prompt |
| `agdt.get-pipeline-id.agent.md` | Get Pipeline ID: Retrieve a pipeline ID by name |
| `agdt.get-project-role-details.agent.md` | Get Role Details: Get Jira project role details |
| `agdt.get-pull-request-details.agent.md` | Get PR Details: Retrieve full pull request details |
| `agdt.get-pull-request-threads.agent.md` | Get PR Threads: Retrieve all comment threads |
| `agdt.get-run-details.agent.md` | Get Run Details: Retrieve pipeline run details |
| `agdt.get-workflow.agent.md` | Get Workflow: Display current workflow state |
| `agdt.get.agent.md` | Get State Value: Retrieve a value from the agdt state |
| `agdt.git-force-push.agent.md` | Git Force Push: Force push to origin |
| `agdt.git-publish.agent.md` | Git Publish: Publish branch upstream |
| `agdt.git-push.agent.md` | Git Push: Push to origin |
| `agdt.git-save-work.agent.md` | Git Save Work: Stage, commit/amend, and push changes |
| `agdt.git-stage.agent.md` | Git Stage: Stage all changes |
| `agdt.git-sync.agent.md` | Git Sync: Sync local branch with remote |
| `agdt.list-pipelines.agent.md` | List Pipelines: List Azure DevOps pipelines |
| `agdt.list-project-roles.agent.md` | List Project Roles: List Jira project roles |
| `agdt.mark-file-reviewed.agent.md` | Mark File Reviewed: Mark a file as reviewed |
| `agdt.mark-pull-request-draft.agent.md` | Mark PR Draft: Mark a pull request as draft |
| `agdt.network-status.agent.md` | Network Status: Check network connectivity |
| `agdt.optimize-issue-for-ai-agent.initiate.agent.md` | Optimize Issue for AI Agent - Initiate: Optimize a Jira issue for AI agent consumption |
| `agdt.parse-jira-error-report.agent.md` | Parse Error Report: Parse a Jira error report |
| `agdt.pr-merge-execute.agent.md` | Narrowly-scoped agent responsible solely for executing the merge command with error handling and retries |
| `agdt.pr-merge-manager.agent.md` | PR Merge Manager: Poll PR state, address Copilot review comments, approve and merge when green |
| `agdt.publish-pull-request.agent.md` | Publish PR: Publish a draft pull request |
| `agdt.pull-request-review.completion.agent.md` | PR Review - Completion: Finalize review (step 4 of 4) |
| `agdt.pull-request-review.decision.agent.md` | PR Review - Decision: Approve or request changes (step 3 of 4) |
| `agdt.pull-request-review.file-review.agent.md` | PR Review - File Review: Review individual files (step 2 of 4) |
| `agdt.pull-request-review.initiate.agent.md` | PR Review - Initiate: Start a pull request review (step 1 of 4) |
| `agdt.query-app-insights.agent.md` | Query App Insights: Run an Azure App Insights query |
| `agdt.query-fabric-dap-errors.agent.md` | Query Fabric DAP Errors: Query Fabric DAP error logs |
| `agdt.query-fabric-dap-provisioning.agent.md` | Query Fabric DAP Provisioning: Query provisioning logs |
| `agdt.query-fabric-dap-timeline.agent.md` | Query Fabric DAP Timeline: Query timeline logs |
| `agdt.reject-suggestion-resolution.agent.md` | Reject Suggestion: Reject a suggestion resolution |
| `agdt.release-pypi.agent.md` | Release to PyPI: Publish package to PyPI |
| `agdt.reply-to-pull-request-thread.agent.md` | Reply to PR Thread: Reply to a comment thread |
| `agdt.request-changes-with-suggestion.agent.md` | Request Changes with Suggestion: Request changes with code suggestions |
| `agdt.request-changes.agent.md` | Request Changes: Request changes on a file |
| `agdt.resolve-merge-conflicts.agent.md` | Resolve Merge Conflicts: Resolve merge conflicts systematically |
| `agdt.resolve-thread.agent.md` | Resolve Thread: Resolve a PR comment thread |
| `agdt.review.agent.md` | Multi-Model Review: Run multi-model review pipeline |
| `agdt.run-e2e-tests-fabric.agent.md` | Run E2E Tests Fabric: Trigger Fabric E2E test pipeline |
| `agdt.run-e2e-tests-synapse.agent.md` | Run E2E Tests Synapse: Trigger Synapse E2E test pipeline |
| `agdt.run-wb-patch.agent.md` | Run Workbench Patch: Trigger workbench patch pipeline |
| `agdt.set.agent.md` | Set State Value: Set a key-value pair in the agdt state |
| `agdt.setup-certs.agent.md` | Setup Certificates: Set up SSL certificates |
| `agdt.setup-check.agent.md` | Setup Check: Verify setup configuration |
| `agdt.setup-copilot-cli.agent.md` | Setup Copilot CLI: Set up GitHub Copilot CLI |
| `agdt.setup-gh-cli.agent.md` | Setup GitHub CLI: Set up GitHub CLI |
| `agdt.setup-worktree-background.agent.md` | Setup Worktree: Set up a git worktree in the background |
| `agdt.setup.agent.md` | Setup: Run full agentic-devtools setup |
| `agdt.show-checklist.agent.md` | Show Checklist: Display current checklist |
| `agdt.show-other-incomplete-tasks.agent.md` | Show Incomplete Tasks: Show other incomplete background tasks |
| `agdt.show.agent.md` | Show State: Display all current state values |
| `agdt.squash-commits.agent.md` | Squash Commits: Squash multiple commits into a single well-formed commit |
| `agdt.submit-file-review.agent.md` | Submit File Review: Submit batched file review |
| `agdt.task-log.agent.md` | Task Log: Display task output log |
| `agdt.task-status.agent.md` | Task Status: Show detailed task status |
| `agdt.task-wait.agent.md` | Task Wait: Wait for task completion |
| `agdt.tasks-clean.agent.md` | Tasks Clean: Clean up expired tasks |
| `agdt.tasks.agent.md` | List Tasks: List all background tasks |
| `agdt.test-file.agent.md` | Test File: Run tests for a specific source file |
| `agdt.test-pattern.agent.md` | Test Pattern: Run specific tests by pattern |
| `agdt.test-quick.agent.md` | Run Tests Quick: Run tests without coverage |
| `agdt.test.agent.md` | Run Tests: Run full test suite with coverage |
| `agdt.update-checklist.agent.md` | Update Checklist: Update checklist items in the active workflow |
| `agdt.update-jira-issue.agent.md` | Update Jira Issue: Update Jira issue fields |
| `agdt.update-jira-issue.initiate.agent.md` | Update Jira Issue - Initiate: Update an existing Jira issue |
| `agdt.update-pipeline.agent.md` | Update Pipeline: Update an Azure DevOps pipeline |
| `agdt.vpn-off.agent.md` | VPN Off: Disconnect from VPN |
| `agdt.vpn-on.agent.md` | VPN On: Connect to VPN |
| `agdt.vpn-run.agent.md` | VPN Run: Run a command with automatic VPN context management |
| `agdt.vpn-status.agent.md` | agdt.vpn-status agent for checking VPN connection status. |
| `agdt.wait-for-run.agent.md` | Wait for Run: Start a background task to monitor a pipeline run |
| `agdt.work-on-jira-issue.checklist-creation.agent.md` | Work on Jira Issue - Checklist Creation: Create implementation checklist (step 5 of 11) |
| `agdt.work-on-jira-issue.commit.agent.md` | Work on Jira Issue - Commit: Stage and commit changes (step 9 of 11) |
| `agdt.work-on-jira-issue.completion.agent.md` | Work on Jira Issue - Completion: Post final Jira comment (step 11 of 11) |
| `agdt.work-on-jira-issue.implementation-review.agent.md` | Work on Jira Issue - Implementation Review: Review completed checklist (step 7 of 11) |
| `agdt.work-on-jira-issue.implementation.agent.md` | Work on Jira Issue - Implementation: Implement checklist items (step 6 of 11) |
| `agdt.work-on-jira-issue.initiate.agent.md` | Work on Jira Issue - Initiate: Start working on a Jira issue (step 1 of 11) |
| `agdt.work-on-jira-issue.planning.agent.md` | Work on Jira Issue - Planning: Analyze issue and post plan (step 4 of 11) |
| `agdt.work-on-jira-issue.pull-request.agent.md` | Work on Jira Issue - Pull Request: Create a pull request (step 10 of 11) |
| `agdt.work-on-jira-issue.retrieve.agent.md` | Work on Jira Issue - Retrieve: Fetch Jira issue details (step 3 of 11) |
| `agdt.work-on-jira-issue.setup.agent.md` | Work on Jira Issue - Setup: Create worktree and branch (step 2 of 11) |
| `agdt.work-on-jira-issue.verification.agent.md` | Work on Jira Issue - Verification: Run tests and quality gates (step 8 of 11) |

## Regeneration

Run `agdt-setup` to update these files.  Stale files (removed in newer
package versions) are automatically cleaned up.
