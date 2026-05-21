"""Tests for GitHubActionsProvider.list_pr_issue_events()."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider
from agentic_devtools.cli.ci.models import (
    COPILOT_SESSION_EVENT_FINISHED,
    COPILOT_SESSION_EVENT_FINISHED_FAILURE,
    COPILOT_SESSION_EVENT_STARTED,
    IssueEvent,
)


def _make_raw_event(event_type: str, event_id: int = 1, actor_login: str = "Copilot") -> dict:
    return {
        "id": event_id,
        "event": event_type,
        "created_at": "2026-05-20T06:05:00Z",
        "actor": {"login": actor_login},
    }


class TestListPrIssueEvents:
    """Tests for GitHubActionsProvider.list_pr_issue_events()."""

    def test_returns_only_copilot_session_events(self) -> None:
        """Filters non-Copilot events and returns only session events."""
        raw_events = [
            _make_raw_event("labeled", event_id=1),
            _make_raw_event(COPILOT_SESSION_EVENT_STARTED, event_id=2),
            _make_raw_event("assigned", event_id=3),
            _make_raw_event(COPILOT_SESSION_EVENT_FINISHED, event_id=4),
        ]
        provider = GitHubActionsProvider(repo="owner/repo")
        with (
            patch("agentic_devtools.cli.ci.github_provider._gh_api") as mock_gh_api,
            patch(
                "agentic_devtools.cli.ci.github_provider._parse_paginated_json",
                return_value=raw_events,
            ),
        ):
            mock_gh_api.return_value = MagicMock()
            result = provider.list_pr_issue_events(42)

        assert len(result) == 2
        assert result[0].event == COPILOT_SESSION_EVENT_STARTED
        assert result[1].event == COPILOT_SESSION_EVENT_FINISHED

    def test_returns_events_in_ascending_id_order(self) -> None:
        """Events are sorted by id ascending regardless of API order."""
        raw_events = [
            _make_raw_event(COPILOT_SESSION_EVENT_FINISHED, event_id=10),
            _make_raw_event(COPILOT_SESSION_EVENT_STARTED, event_id=5),
        ]
        provider = GitHubActionsProvider(repo="owner/repo")
        with (
            patch("agentic_devtools.cli.ci.github_provider._gh_api") as mock_gh_api,
            patch(
                "agentic_devtools.cli.ci.github_provider._parse_paginated_json",
                return_value=raw_events,
            ),
        ):
            mock_gh_api.return_value = MagicMock()
            result = provider.list_pr_issue_events(42)

        assert result[0].id == 5
        assert result[1].id == 10

    def test_returns_empty_list_when_no_session_events(self) -> None:
        """Returns empty list when no Copilot session events are found."""
        raw_events = [
            _make_raw_event("labeled", event_id=1),
            _make_raw_event("assigned", event_id=2),
        ]
        provider = GitHubActionsProvider(repo="owner/repo")
        with (
            patch("agentic_devtools.cli.ci.github_provider._gh_api") as mock_gh_api,
            patch(
                "agentic_devtools.cli.ci.github_provider._parse_paginated_json",
                return_value=raw_events,
            ),
        ):
            mock_gh_api.return_value = MagicMock()
            result = provider.list_pr_issue_events(42)

        assert result == []

    def test_populates_issue_event_fields(self) -> None:
        """Correctly populates all IssueEvent fields from raw API response."""
        raw_events = [
            {
                "id": 99,
                "event": COPILOT_SESSION_EVENT_FINISHED_FAILURE,
                "created_at": "2026-05-20T08:00:00Z",
                "actor": {"login": "Copilot"},
            }
        ]
        provider = GitHubActionsProvider(repo="owner/repo")
        with (
            patch("agentic_devtools.cli.ci.github_provider._gh_api") as mock_gh_api,
            patch(
                "agentic_devtools.cli.ci.github_provider._parse_paginated_json",
                return_value=raw_events,
            ),
        ):
            mock_gh_api.return_value = MagicMock()
            result = provider.list_pr_issue_events(42)

        assert len(result) == 1
        event = result[0]
        assert isinstance(event, IssueEvent)
        assert event.id == 99
        assert event.event == COPILOT_SESSION_EVENT_FINISHED_FAILURE
        assert event.created_at == "2026-05-20T08:00:00Z"
        assert event.actor_login == "Copilot"

    def test_handles_null_actor(self) -> None:
        """Handles null actor gracefully — actor_login defaults to empty string."""
        raw_events = [
            {
                "id": 77,
                "event": COPILOT_SESSION_EVENT_FINISHED,
                "created_at": "2026-05-20T08:00:00Z",
                "actor": None,
            }
        ]
        provider = GitHubActionsProvider(repo="owner/repo")
        with (
            patch("agentic_devtools.cli.ci.github_provider._gh_api") as mock_gh_api,
            patch(
                "agentic_devtools.cli.ci.github_provider._parse_paginated_json",
                return_value=raw_events,
            ),
        ):
            mock_gh_api.return_value = MagicMock()
            result = provider.list_pr_issue_events(42)

        assert len(result) == 1
        assert result[0].actor_login == ""
