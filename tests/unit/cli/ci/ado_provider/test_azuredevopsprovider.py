"""Tests for AzureDevOpsProvider stub."""

import pytest

from agentic_devtools.cli.ci.ado_provider import AzureDevOpsProvider
from agentic_devtools.cli.ci.models import EventPayload, ReviewCommentInfo
from agentic_devtools.cli.ci.provider import CIPlatformProvider


class TestAzureDevOpsProvider:
    """Tests for the AzureDevOpsProvider stub."""

    def test_satisfies_abc(self) -> None:
        """ADO provider satisfies the CIPlatformProvider ABC."""
        provider = AzureDevOpsProvider(organization="myorg", project="myproject")
        assert isinstance(provider, CIPlatformProvider)

    def test_parse_event_pr_updated(self) -> None:
        """Parses ADO pullrequest.updated service hook payload."""
        provider = AzureDevOpsProvider()
        raw = {
            "resource": {
                "pullRequestId": 42,
                "sourceRefName": "refs/heads/feature/test",
                "targetRefName": "refs/heads/main",
                "lastMergeSourceCommit": {"commitId": "abc123def456"},
                "repository": {"name": "my-repo"},
            },
            "resourceContainers": {"project": {"id": "my-project"}},
        }
        result = provider.parse_event(raw, "git.pullrequest.updated")

        assert isinstance(result, EventPayload)
        assert result.pr_number == 42
        assert result.head_branch == "feature/test"
        assert result.base_branch == "main"
        assert result.head_sha == "abc123def456"
        assert result.action == "edited"
        assert result.repository_full_name == "my-project/my-repo"

    def test_parse_event_empty_payload(self) -> None:
        """Empty payload returns zeroed EventPayload."""
        provider = AzureDevOpsProvider()
        result = provider.parse_event({}, "git.pullrequest.created")
        assert result.pr_number == 0
        assert result.head_branch == ""
        assert result.head_sha == ""

    def test_parse_event_string_pr_id(self) -> None:
        """Handles string pullRequestId gracefully."""
        provider = AzureDevOpsProvider()
        raw = {"resource": {"pullRequestId": "99"}}
        result = provider.parse_event(raw, "git.pullrequest.updated")
        assert result.pr_number == 99

    def test_parse_event_non_numeric_pr_id(self) -> None:
        """Non-numeric pullRequestId defaults to 0."""
        provider = AzureDevOpsProvider()
        raw = {"resource": {"pullRequestId": "not-a-number"}}
        result = provider.parse_event(raw, "git.pullrequest.updated")
        assert result.pr_number == 0

    def test_action_methods_raise_not_implemented(self) -> None:
        """All action methods raise NotImplementedError."""
        provider = AzureDevOpsProvider()
        with pytest.raises(NotImplementedError):
            provider.get_pr_metadata(1)
        with pytest.raises(NotImplementedError):
            provider.list_check_runs("sha")
        with pytest.raises(NotImplementedError):
            provider.list_reviews(1)
        with pytest.raises(NotImplementedError):
            provider.post_comment(1, "body")
        with pytest.raises(NotImplementedError):
            provider.update_comment(1, "body")
        with pytest.raises(NotImplementedError):
            provider.find_comment(1, "marker")
        with pytest.raises(NotImplementedError):
            provider.approve_pr(1, "sha", "body")
        with pytest.raises(NotImplementedError):
            provider.merge_pr(1, "sha", "squash")
        with pytest.raises(NotImplementedError):
            provider.request_reviewer(1, "user")
        with pytest.raises(NotImplementedError):
            provider.publish_pr(1)
        with pytest.raises(NotImplementedError):
            provider.squash_before_publish(
                pr_number=1,
                base_branch="main",
                head_branch="feature/test",
                head_sha="abc123",
            )
        with pytest.raises(NotImplementedError):
            provider.list_pr_files(1)
        with pytest.raises(NotImplementedError):
            provider.get_check_annotations(1, 10)
        with pytest.raises(NotImplementedError):
            provider.dispatch_repair(
                1,
                "sha",
                "review",
                [],
                [ReviewCommentInfo(id=1, path="file.py", body="comment", html_url="")],
                review_id=1,
            )
        with pytest.raises(NotImplementedError):
            provider.list_review_comments(1, 1)
        with pytest.raises(NotImplementedError):
            provider.finalize_post_repair(
                pr_number=1,
                base_branch="main",
                head_branch="feature/test",
                head_sha="abc123",
                review_id=1,
            )
        with pytest.raises(NotImplementedError):
            provider.squash_post_repair(
                pr_number=1,
                base_branch="main",
                head_branch="feature/test",
                head_sha="abc123",
            )

    def test_list_pr_issue_events_returns_empty_list(self) -> None:
        """ADO provider list_pr_issue_events always returns an empty list."""
        provider = AzureDevOpsProvider()
        result = provider.list_pr_issue_events(42)
        assert result == []

    def test_malformed_payload_raises_error(self) -> None:
        """Payload that causes TypeError/ValueError raises MalformedEventError."""
        from agentic_devtools.cli.ci.exceptions import MalformedEventError

        provider = AzureDevOpsProvider()
        # resource.get will fail if resource is not a dict
        raw = {"resource": None}  # type: ignore[dict-item]
        with pytest.raises(MalformedEventError):
            provider.parse_event(raw, "git.pullrequest.updated")

    def test_parse_event_pr_updated_with_title_change(self) -> None:
        """PR updated event with changedFields.title sets title_changed."""
        provider = AzureDevOpsProvider()
        raw = {
            "resource": {
                "pullRequestId": 42,
                "sourceRefName": "refs/heads/feature/test",
                "targetRefName": "refs/heads/main",
                "lastMergeSourceCommit": {"commitId": "abc123"},
                "repository": {"name": "my-repo"},
            },
            "resourceContainers": {"project": {"id": "my-project"}},
            "changedFields": {"title": {"oldValue": "Old", "newValue": "New"}},
        }
        result = provider.parse_event(raw, "git.pullrequest.updated")
        assert result.action == "edited"
        assert result.edit_changes_known is True
        assert result.title_changed is True
        assert result.body_changed is False
        assert result.base_changed is False

    def test_parse_event_pr_updated_description_only(self) -> None:
        """PR updated event with only description change sets body_changed."""
        provider = AzureDevOpsProvider()
        raw = {
            "resource": {
                "pullRequestId": 42,
                "sourceRefName": "refs/heads/feature/test",
                "targetRefName": "refs/heads/main",
                "lastMergeSourceCommit": {"commitId": "abc123"},
                "repository": {"name": "my-repo"},
            },
            "resourceContainers": {"project": {"id": "my-project"}},
            "changedFields": {"description": {"oldValue": "old", "newValue": "new"}},
        }
        result = provider.parse_event(raw, "git.pullrequest.updated")
        assert result.edit_changes_known is True
        assert result.title_changed is False
        assert result.body_changed is True

    def test_parse_event_pr_updated_target_ref_change(self) -> None:
        """PR updated event with targetRefName change sets base_changed."""
        provider = AzureDevOpsProvider()
        raw = {
            "resource": {
                "pullRequestId": 42,
                "sourceRefName": "refs/heads/feature/test",
                "targetRefName": "refs/heads/main",
                "lastMergeSourceCommit": {"commitId": "abc123"},
                "repository": {"name": "my-repo"},
            },
            "resourceContainers": {"project": {"id": "my-project"}},
            "changedFields": {"targetRefName": {"oldValue": "refs/heads/develop", "newValue": "refs/heads/main"}},
        }
        result = provider.parse_event(raw, "git.pullrequest.updated")
        assert result.edit_changes_known is True
        assert result.base_changed is True

    def test_parse_event_pr_updated_no_changed_fields(self) -> None:
        """PR updated event without changedFields keeps defaults (fail-open)."""
        provider = AzureDevOpsProvider()
        raw = {
            "resource": {
                "pullRequestId": 42,
                "sourceRefName": "refs/heads/feature/test",
                "targetRefName": "refs/heads/main",
                "lastMergeSourceCommit": {"commitId": "abc123"},
                "repository": {"name": "my-repo"},
            },
            "resourceContainers": {"project": {"id": "my-project"}},
        }
        result = provider.parse_event(raw, "git.pullrequest.updated")
        assert result.action == "edited"
        assert result.edit_changes_known is False
        assert result.title_changed is False
        assert result.body_changed is False
        assert result.base_changed is False

    def test_parse_event_pr_updated_empty_changed_fields_marks_known(self) -> None:
        """PR updated event with empty changedFields is known but irrelevant."""
        provider = AzureDevOpsProvider()
        raw = {
            "resource": {
                "pullRequestId": 42,
                "sourceRefName": "refs/heads/feature/test",
                "targetRefName": "refs/heads/main",
                "lastMergeSourceCommit": {"commitId": "abc123"},
                "repository": {"name": "my-repo"},
            },
            "resourceContainers": {"project": {"id": "my-project"}},
            "changedFields": {},
        }
        result = provider.parse_event(raw, "git.pullrequest.updated")
        assert result.action == "edited"
        assert result.edit_changes_known is True
        assert result.title_changed is False
        assert result.body_changed is False
        assert result.base_changed is False

    def test_parse_event_non_update_event_keeps_defaults(self) -> None:
        """Non-update events keep all edit fields at defaults."""
        provider = AzureDevOpsProvider()
        raw = {
            "resource": {
                "pullRequestId": 10,
                "sourceRefName": "refs/heads/feature/x",
                "targetRefName": "refs/heads/main",
                "lastMergeSourceCommit": {"commitId": "def456"},
                "repository": {"name": "my-repo"},
            },
            "resourceContainers": {"project": {"id": "proj"}},
        }
        result = provider.parse_event(raw, "git.pullrequest.created")
        assert result.action == "git.pullrequest.created"
        assert result.edit_changes_known is False
        assert result.title_changed is False
