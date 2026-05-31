"""Tests for GitHubActionsProvider.parse_event() method."""

import json
from pathlib import Path

import pytest

from agentic_devtools.cli.ci.exceptions import MalformedEventError
from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider
from agentic_devtools.cli.ci.models import EventPayload

FIXTURES_DIR = Path(__file__).resolve().parents[4] / "fixtures" / "ci_events"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text())


class TestParseEvent:
    """Tests for GitHubActionsProvider.parse_event()."""

    def test_pull_request_opened(self) -> None:
        provider = GitHubActionsProvider(repo="owner/repo")
        payload = _load_fixture("pull_request_opened.json")
        result = provider.parse_event(payload, "pull_request")
        assert isinstance(result, EventPayload)
        assert result.pr_number == 42
        assert result.head_branch == "feature/new-feature"
        assert result.head_sha == "abc123def456789012345678901234567890abcd"
        assert result.base_branch == "main"
        assert result.action == "opened"
        assert result.repository_full_name == "owner/repo"
        assert result.sender_login == "contributor"

    def test_pull_request_synchronize(self) -> None:
        provider = GitHubActionsProvider(repo="owner/repo")
        payload = _load_fixture("pull_request_synchronize.json")
        result = provider.parse_event(payload, "pull_request")
        assert result.pr_number == 42
        assert result.head_sha == "def456abc789012345678901234567890abcdef01"
        assert result.action == "synchronize"
        assert result.sender_login == "Copilot"

    def test_pull_request_review_submitted(self) -> None:
        provider = GitHubActionsProvider(repo="owner/repo")
        payload = _load_fixture("pull_request_review_submitted.json")
        result = provider.parse_event(payload, "pull_request_review")
        assert result.pr_number == 42
        assert result.head_branch == "feature/new-feature"
        assert result.action == "submitted"
        assert result.sender_login == "reviewer1"

    def test_workflow_run_completed(self) -> None:
        provider = GitHubActionsProvider(repo="owner/repo")
        payload = _load_fixture("workflow_run_completed.json")
        result = provider.parse_event(payload, "workflow_run")
        assert result.pr_number == 42
        assert result.head_branch == "feature/new-feature"
        assert result.head_sha == "abc123def456789012345678901234567890abcd"
        assert result.action == "completed"

    def test_issue_comment_created_for_pull_request(self) -> None:
        provider = GitHubActionsProvider(repo="owner/repo")
        payload = _load_fixture("issue_comment_created.json")
        result = provider.parse_event(payload, "issue_comment")
        assert result.pr_number == 42
        assert result.action == "comment_created"
        assert result.repository_full_name == "owner/repo"
        assert result.sender_login == "copilot[bot]"

    def test_malformed_payload_missing_pull_request(self) -> None:
        provider = GitHubActionsProvider(repo="owner/repo")
        with pytest.raises(MalformedEventError) as exc_info:
            provider.parse_event({}, "pull_request")
        assert exc_info.value.event_name == "pull_request"

    def test_malformed_payload_missing_review_pr(self) -> None:
        provider = GitHubActionsProvider(repo="owner/repo")
        with pytest.raises(MalformedEventError):
            provider.parse_event({"action": "submitted"}, "pull_request_review")

    def test_unsupported_event_type(self) -> None:
        provider = GitHubActionsProvider(repo="owner/repo")
        with pytest.raises(MalformedEventError) as exc_info:
            provider.parse_event({}, "deployment")
        assert "unsupported event type" in exc_info.value.reason

    def test_mismatched_event_name(self) -> None:
        """Using issues payload with pull_request event_name raises error."""
        provider = GitHubActionsProvider(repo="owner/repo")
        issues_payload = _load_fixture("issues_labeled.json")
        with pytest.raises(MalformedEventError):
            provider.parse_event(issues_payload, "pull_request")

    def test_workflow_run_missing_field(self) -> None:
        """workflow_run event without workflow_run field raises error."""
        provider = GitHubActionsProvider(repo="owner/repo")
        with pytest.raises(MalformedEventError, match="missing 'workflow_run' field"):
            provider.parse_event({"action": "completed"}, "workflow_run")

    def test_issue_comment_without_issue_field_raises_error(self) -> None:
        provider = GitHubActionsProvider(repo="owner/repo")
        with pytest.raises(MalformedEventError, match="missing 'issue' field"):
            provider.parse_event({"action": "created"}, "issue_comment")

    def test_issue_comment_on_issue_not_pr_raises_error(self) -> None:
        provider = GitHubActionsProvider(repo="owner/repo")
        payload = {
            "action": "created",
            "issue": {"number": 42},
            "repository": {"full_name": "owner/repo"},
        }
        with pytest.raises(MalformedEventError, match="not on a pull request"):
            provider.parse_event(payload, "issue_comment")

    def test_issue_comment_missing_issue_number_raises_error(self) -> None:
        provider = GitHubActionsProvider(repo="owner/repo")
        payload = {
            "action": "created",
            "issue": {"pull_request": {"url": "https://api.github.com/repos/owner/repo/pulls/42"}},
            "repository": {"full_name": "owner/repo"},
        }
        with pytest.raises(MalformedEventError, match="missing or invalid 'issue.number' field"):
            provider.parse_event(payload, "issue_comment")

    def test_issue_comment_non_positive_issue_number_raises_error(self) -> None:
        provider = GitHubActionsProvider(repo="owner/repo")
        payload = {
            "action": "created",
            "issue": {"number": 0, "pull_request": {"url": "https://api.github.com/repos/owner/repo/pulls/42"}},
            "repository": {"full_name": "owner/repo"},
        }
        with pytest.raises(MalformedEventError, match="missing or invalid 'issue.number' field"):
            provider.parse_event(payload, "issue_comment")

    def test_empty_repo_uses_relative_path(self) -> None:
        """When repo is empty, _repo_api returns the path as-is."""
        provider = GitHubActionsProvider(repo="")
        assert provider._repo_api("/pulls/1") == "/pulls/1"

    def test_workflow_dispatch_with_pr_number(self) -> None:
        """workflow_dispatch event with pr_number input → action='completed'."""
        provider = GitHubActionsProvider(repo="owner/repo")
        payload = {
            "inputs": {"pr_number": "42", "trigger_reason": "squash_wait_scheduler"},
            "repository": {"full_name": "owner/repo"},
            "sender": {"login": "github-actions[bot]"},
        }
        result = provider.parse_event(payload, "workflow_dispatch")
        assert result.pr_number == 42
        assert result.action == "completed"
        assert result.repository_full_name == "owner/repo"

    def test_workflow_dispatch_without_pr_number(self) -> None:
        """workflow_dispatch event with no pr_number → pr_number=0."""
        provider = GitHubActionsProvider(repo="owner/repo")
        payload = {
            "inputs": {},
            "repository": {"full_name": "owner/repo"},
        }
        result = provider.parse_event(payload, "workflow_dispatch")
        assert result.pr_number == 0
        assert result.action == "completed"

    def test_workflow_dispatch_invalid_pr_number_defaults_to_zero(self) -> None:
        """workflow_dispatch event with non-integer pr_number → pr_number=0."""
        provider = GitHubActionsProvider(repo="owner/repo")
        payload = {
            "inputs": {"pr_number": "not-a-number"},
            "repository": {"full_name": "owner/repo"},
        }
        result = provider.parse_event(payload, "workflow_dispatch")
        assert result.pr_number == 0
        assert result.action == "completed"

    def test_pull_request_edited_title_change(self) -> None:
        """Edited event with changes.title populates title_changed."""
        provider = GitHubActionsProvider(repo="owner/repo")
        payload = {
            "action": "edited",
            "changes": {"title": {"from": "[WIP] Old Title"}},
            "pull_request": {
                "number": 42,
                "head": {"ref": "feature/test", "sha": "abc123"},
                "base": {"ref": "main"},
            },
            "repository": {"full_name": "owner/repo"},
            "sender": {"login": "contributor"},
        }
        result = provider.parse_event(payload, "pull_request")
        assert result.action == "edited"
        assert result.edit_changes_known is True
        assert result.title_changed is True
        assert result.body_changed is False
        assert result.base_changed is False

    def test_pull_request_edited_body_only(self) -> None:
        """Edited event with only changes.body populates body_changed."""
        provider = GitHubActionsProvider(repo="owner/repo")
        payload = {
            "action": "edited",
            "changes": {"body": {"from": "old body text"}},
            "pull_request": {
                "number": 42,
                "head": {"ref": "feature/test", "sha": "abc123"},
                "base": {"ref": "main"},
            },
            "repository": {"full_name": "owner/repo"},
            "sender": {"login": "contributor"},
        }
        result = provider.parse_event(payload, "pull_request")
        assert result.edit_changes_known is True
        assert result.title_changed is False
        assert result.body_changed is True
        assert result.base_changed is False

    def test_pull_request_edited_base_change(self) -> None:
        """Edited event with changes.base populates base_changed."""
        provider = GitHubActionsProvider(repo="owner/repo")
        payload = {
            "action": "edited",
            "changes": {"base": {"ref": {"from": "develop"}}},
            "pull_request": {
                "number": 42,
                "head": {"ref": "feature/test", "sha": "abc123"},
                "base": {"ref": "main"},
            },
            "repository": {"full_name": "owner/repo"},
            "sender": {"login": "contributor"},
        }
        result = provider.parse_event(payload, "pull_request")
        assert result.edit_changes_known is True
        assert result.base_changed is True

    def test_pull_request_edited_empty_changes(self) -> None:
        """Edited event with empty changes dict sets edit_changes_known=True."""
        provider = GitHubActionsProvider(repo="owner/repo")
        payload = {
            "action": "edited",
            "changes": {},
            "pull_request": {
                "number": 42,
                "head": {"ref": "feature/test", "sha": "abc123"},
                "base": {"ref": "main"},
            },
            "repository": {"full_name": "owner/repo"},
        }
        result = provider.parse_event(payload, "pull_request")
        assert result.edit_changes_known is True
        assert result.title_changed is False
        assert result.body_changed is False
        assert result.base_changed is False

    def test_pull_request_edited_no_changes_key(self) -> None:
        """Edited event without changes key keeps edit_changes_known=False."""
        provider = GitHubActionsProvider(repo="owner/repo")
        payload = {
            "action": "edited",
            "pull_request": {
                "number": 42,
                "head": {"ref": "feature/test", "sha": "abc123"},
                "base": {"ref": "main"},
            },
            "repository": {"full_name": "owner/repo"},
        }
        result = provider.parse_event(payload, "pull_request")
        assert result.edit_changes_known is False
        assert result.title_changed is False

    @pytest.mark.parametrize("changes", [None, "body"])
    def test_pull_request_edited_non_dict_changes_keeps_unknown(self, changes: object) -> None:
        """Edited event with non-dict changes fails open instead of raising."""
        provider = GitHubActionsProvider(repo="owner/repo")
        payload = {
            "action": "edited",
            "changes": changes,
            "pull_request": {
                "number": 42,
                "head": {"ref": "feature/test", "sha": "abc123"},
                "base": {"ref": "main"},
            },
            "repository": {"full_name": "owner/repo"},
        }
        result = provider.parse_event(payload, "pull_request")
        assert result.edit_changes_known is False
        assert result.title_changed is False
        assert result.body_changed is False
        assert result.base_changed is False

    def test_pull_request_non_edited_has_default_edit_fields(self) -> None:
        """Non-edited events keep all edit fields at defaults."""
        provider = GitHubActionsProvider(repo="owner/repo")
        payload = {
            "action": "opened",
            "pull_request": {
                "number": 42,
                "head": {"ref": "feature/test", "sha": "abc123"},
                "base": {"ref": "main"},
            },
            "repository": {"full_name": "owner/repo"},
        }
        result = provider.parse_event(payload, "pull_request")
        assert result.edit_changes_known is False
        assert result.title_changed is False
        assert result.body_changed is False
        assert result.base_changed is False

    def test_workflow_run_with_no_pull_requests(self) -> None:
        """workflow_run event with empty pull_requests defaults to pr_number=0."""
        provider = GitHubActionsProvider(repo="owner/repo")
        payload = {
            "action": "completed",
            "workflow_run": {
                "id": 9876543,
                "name": "CI",
                "head_branch": "feature/new-feature",
                "head_sha": "abc123",
                "conclusion": "success",
                "pull_requests": [],
            },
            "repository": {"full_name": "owner/repo"},
        }
        result = provider.parse_event(payload, "workflow_run")
        assert result.pr_number == 0
        assert result.head_branch == "feature/new-feature"
        assert result.base_branch == ""
