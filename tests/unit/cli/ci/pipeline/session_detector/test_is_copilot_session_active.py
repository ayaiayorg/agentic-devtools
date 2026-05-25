"""Tests for is_copilot_session_active."""

from unittest.mock import MagicMock

from agentic_devtools.cli.ci.models import IssueEvent
from agentic_devtools.cli.ci.pipeline.session_detector import is_copilot_session_active


class TestIsCopilotSessionActive:
    """Tests for the session detector function."""

    def _make_provider(self, events: list[IssueEvent]) -> MagicMock:
        provider = MagicMock()
        provider.list_pr_issue_events.return_value = events
        return provider

    def test_no_events_returns_false(self) -> None:
        provider = self._make_provider([])
        assert is_copilot_session_active(provider, 1) is False

    def test_started_without_terminal_returns_true(self) -> None:
        events = [IssueEvent(id=1, event="copilot_work_started", created_at="2024-01-01T00:00:00Z")]
        provider = self._make_provider(events)
        assert is_copilot_session_active(provider, 1) is True

    def test_started_with_finished_returns_false(self) -> None:
        events = [
            IssueEvent(id=1, event="copilot_work_started", created_at="2024-01-01T00:00:00Z"),
            IssueEvent(id=2, event="copilot_work_finished", created_at="2024-01-01T01:00:00Z"),
        ]
        provider = self._make_provider(events)
        assert is_copilot_session_active(provider, 1) is False

    def test_started_with_failure_returns_false(self) -> None:
        events = [
            IssueEvent(id=1, event="copilot_work_started", created_at="2024-01-01T00:00:00Z"),
            IssueEvent(id=2, event="copilot_work_finished_failure", created_at="2024-01-01T01:00:00Z"),
        ]
        provider = self._make_provider(events)
        assert is_copilot_session_active(provider, 1) is False

    def test_multiple_sessions_latest_active(self) -> None:
        """When the latest start has no terminal, session is active."""
        events = [
            IssueEvent(id=1, event="copilot_work_started", created_at="2024-01-01T00:00:00Z"),
            IssueEvent(id=2, event="copilot_work_finished", created_at="2024-01-01T01:00:00Z"),
            IssueEvent(id=3, event="copilot_work_started", created_at="2024-01-01T02:00:00Z"),
        ]
        provider = self._make_provider(events)
        assert is_copilot_session_active(provider, 1) is True

    def test_multiple_sessions_latest_finished(self) -> None:
        """When the latest start has a terminal, session is not active."""
        events = [
            IssueEvent(id=1, event="copilot_work_started", created_at="2024-01-01T00:00:00Z"),
            IssueEvent(id=2, event="copilot_work_finished", created_at="2024-01-01T01:00:00Z"),
            IssueEvent(id=3, event="copilot_work_started", created_at="2024-01-01T02:00:00Z"),
            IssueEvent(id=4, event="copilot_work_finished", created_at="2024-01-01T03:00:00Z"),
        ]
        provider = self._make_provider(events)
        assert is_copilot_session_active(provider, 1) is False

    def test_api_failure_returns_true(self) -> None:
        """When API call fails, assume active session (fail-closed)."""
        provider = MagicMock()
        provider.list_pr_issue_events.side_effect = RuntimeError("API error")
        assert is_copilot_session_active(provider, 1) is True
