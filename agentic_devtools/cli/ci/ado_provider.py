"""Azure DevOps CI platform provider stub.

Validates that the ``CIPlatformProvider`` abstraction is extensible to
non-GitHub platforms. Implements basic ``parse_event()`` for ADO service
hook payloads; all action methods raise ``NotImplementedError``.
"""

from __future__ import annotations

from agentic_devtools.cli.ci.exceptions import MalformedEventError
from agentic_devtools.cli.ci.models import (
    CheckRunStatus,
    EventPayload,
    FinalizationResult,
    IssueCommentInfo,
    IssueEvent,
    PRMetadata,
    ReviewCommentInfo,
    ReviewInfo,
)
from agentic_devtools.cli.ci.provider import CIPlatformProvider


class AzureDevOpsProvider(CIPlatformProvider):
    """Azure DevOps stub implementation of the CI platform provider.

    Demonstrates that the abstraction supports non-GitHub CI platforms.
    Only ``parse_event()`` is implemented; all other methods raise
    ``NotImplementedError``.
    """

    def __init__(self, organization: str = "", project: str = "") -> None:
        """Initialize the Azure DevOps provider.

        Args:
            organization: Azure DevOps organization name.
            project: Azure DevOps project name.
        """
        self._organization = organization
        self._project = project

    def parse_event(self, raw_payload: dict, event_name: str) -> EventPayload:
        """Parse an Azure DevOps service hook payload.

        Handles the ADO service hook JSON format for pull request events.

        Args:
            raw_payload: Raw JSON payload from the ADO service hook.
            event_name: Event type (e.g., "git.pullrequest.updated").

        Returns:
            Normalized EventPayload.

        Raises:
            MalformedEventError: If the payload cannot be parsed.
        """
        try:
            resource = raw_payload.get("resource", {})

            # ADO PR events have pullRequestId in the resource
            pr_id = resource.get("pullRequestId", 0)
            if isinstance(pr_id, str):
                pr_id = int(pr_id) if pr_id.isdigit() else 0

            # Extract branch info
            source_branch = resource.get("sourceRefName", "")
            target_branch = resource.get("targetRefName", "")
            # Strip refs/heads/ prefix
            if source_branch.startswith("refs/heads/"):
                source_branch = source_branch[len("refs/heads/") :]
            if target_branch.startswith("refs/heads/"):
                target_branch = target_branch[len("refs/heads/") :]

            # Extract commit SHA
            last_merge_source_commit = resource.get("lastMergeSourceCommit", {})
            head_sha = last_merge_source_commit.get("commitId", "")

            # Extract repository info
            repo_info = resource.get("repository", {})
            repo_name = repo_info.get("name", "")
            project_name = raw_payload.get("resourceContainers", {}).get("project", {}).get("id", "")
            full_name = f"{project_name}/{repo_name}" if project_name and repo_name else ""

            # Detect edit-change metadata for PR update events
            action = event_name
            title_changed = False
            body_changed = False
            base_changed = False
            edit_changes_known = False
            if event_name == "git.pullrequest.updated":
                action = "edited"
                # ADO includes a "changedFields" dict or per-field deltas in resource
                changed_fields = raw_payload.get("changedFields")
                edit_changes_known = isinstance(changed_fields, dict)
                if isinstance(changed_fields, dict):
                    title_changed = "title" in changed_fields or "Title" in changed_fields
                    body_changed = "description" in changed_fields or "Description" in changed_fields
                    base_changed = "targetRefName" in changed_fields or "TargetRefName" in changed_fields

            return EventPayload(
                pr_number=pr_id,
                head_branch=source_branch,
                head_sha=head_sha,
                base_branch=target_branch,
                action=action,
                repository_full_name=full_name,
                title_changed=title_changed,
                body_changed=body_changed,
                base_changed=base_changed,
                edit_changes_known=edit_changes_known,
            )
        except (TypeError, ValueError, AttributeError) as exc:
            raise MalformedEventError(event_name, str(exc)) from exc

    def get_pr_metadata(self, pr_number: int) -> PRMetadata:
        """Not implemented for ADO stub."""
        raise NotImplementedError("AzureDevOpsProvider.get_pr_metadata() not yet implemented")

    def list_check_runs(self, head_sha: str) -> list[CheckRunStatus]:
        """Not implemented for ADO stub."""
        raise NotImplementedError("AzureDevOpsProvider.list_check_runs() not yet implemented")

    def list_reviews(self, pr_number: int) -> list[ReviewInfo]:
        """Not implemented for ADO stub."""
        raise NotImplementedError("AzureDevOpsProvider.list_reviews() not yet implemented")

    def post_comment(self, pr_number: int, body: str) -> int:
        """Not implemented for ADO stub."""
        raise NotImplementedError("AzureDevOpsProvider.post_comment() not yet implemented")

    def update_comment(self, comment_id: int, body: str) -> None:
        """Not implemented for ADO stub."""
        raise NotImplementedError("AzureDevOpsProvider.update_comment() not yet implemented")

    def find_comment(self, pr_number: int, marker: str) -> tuple[int, str] | None:
        """Not implemented for ADO stub."""
        raise NotImplementedError("AzureDevOpsProvider.find_comment() not yet implemented")

    def approve_pr(self, pr_number: int, head_sha: str, body: str) -> bool:
        """Not implemented for ADO stub."""
        raise NotImplementedError("AzureDevOpsProvider.approve_pr() not yet implemented")

    def merge_pr(self, pr_number: int, head_sha: str, method: str, *, commit_title: str | None = None) -> None:
        """Not implemented for ADO stub."""
        raise NotImplementedError("AzureDevOpsProvider.merge_pr() not yet implemented")

    def publish_pr(self, pr_number: int) -> None:
        """Not implemented for ADO stub."""
        raise NotImplementedError("AzureDevOpsProvider.publish_pr() not yet implemented")

    def squash_before_publish(
        self,
        *,
        pr_number: int,
        base_branch: str,
        head_branch: str,
        head_sha: str,
    ) -> None:
        """Not implemented for ADO stub."""
        raise NotImplementedError("AzureDevOpsProvider.squash_before_publish() not yet implemented")

    def request_reviewer(self, pr_number: int, reviewer: str) -> None:
        """Not implemented for ADO stub."""
        raise NotImplementedError("AzureDevOpsProvider.request_reviewer() not yet implemented")

    def count_unresolved_review_threads(self, pr_number: int) -> int:
        """Not implemented for ADO stub."""
        raise NotImplementedError("AzureDevOpsProvider.count_unresolved_review_threads() not yet implemented")

    def list_pr_files(self, pr_number: int) -> list[str]:
        """Not implemented for ADO stub."""
        raise NotImplementedError("AzureDevOpsProvider.list_pr_files() not yet implemented")

    def get_check_annotations(self, check_run_id: int, limit: int) -> list[str]:
        """Not implemented for ADO stub."""
        raise NotImplementedError("AzureDevOpsProvider.get_check_annotations() not yet implemented")

    def dispatch_repair(
        self,
        pr_number: int,
        head_sha: str,
        repair_type: str,
        failed_checks: list[CheckRunStatus],
        review_comments: list[ReviewCommentInfo],
        review_id: int = 0,
    ) -> int:
        """Not implemented for ADO stub."""
        raise NotImplementedError("AzureDevOpsProvider.dispatch_repair() not yet implemented")

    def list_review_comments(self, pr_number: int, review_id: int) -> list[ReviewCommentInfo]:
        """Not implemented for ADO stub."""
        raise NotImplementedError("AzureDevOpsProvider.list_review_comments() not yet implemented")

    def list_issue_comments(self, pr_number: int) -> list[IssueCommentInfo]:
        """Not implemented for ADO stub."""
        raise NotImplementedError("AzureDevOpsProvider.list_issue_comments() not yet implemented")

    def finalize_post_repair(
        self,
        *,
        pr_number: int,
        base_branch: str,
        head_branch: str,
        head_sha: str,
        review_id: int,
    ) -> FinalizationResult:
        """Not implemented for ADO stub."""
        raise NotImplementedError("AzureDevOpsProvider.finalize_post_repair() not yet implemented")

    def squash_post_repair(
        self,
        *,
        pr_number: int,
        base_branch: str,
        head_branch: str,
        head_sha: str,
    ) -> None:
        """Not implemented for ADO stub."""
        raise NotImplementedError("AzureDevOpsProvider.squash_post_repair() not yet implemented")

    def list_pr_issue_events(self, pr_number: int) -> list[IssueEvent]:
        """ADO does not support the GitHub Issues Events API — returns empty list."""
        return []

    def count_commits_behind(self, *, pr_number: int, base_branch: str, head_branch: str) -> int:
        """ADO stub — returns 0 (not yet implemented)."""
        return 0

    def rebase_onto_base(
        self,
        *,
        pr_number: int,
        base_branch: str,
        head_branch: str,
        head_sha: str,
    ) -> None:
        """Not implemented for ADO stub."""
        raise NotImplementedError("AzureDevOpsProvider.rebase_onto_base() not yet implemented")
