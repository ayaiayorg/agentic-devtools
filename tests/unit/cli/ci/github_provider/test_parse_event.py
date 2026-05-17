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

    def test_empty_repo_uses_relative_path(self) -> None:
        """When repo is empty, _repo_api returns the path as-is."""
        provider = GitHubActionsProvider(repo="")
        assert provider._repo_api("/pulls/1") == "/pulls/1"
