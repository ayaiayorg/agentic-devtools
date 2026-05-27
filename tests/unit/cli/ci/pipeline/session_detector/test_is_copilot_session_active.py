"""Tests for is_copilot_session_active."""

import os
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from agentic_devtools.cli.ci.models import IssueEvent
from agentic_devtools.cli.ci.pipeline.session_detector import (
    _DEFAULT_MAX_SESSION_AGE_SECONDS,
    _is_session_stale,
    is_copilot_session_active,
)


def _recent_timestamp(seconds_ago: int = 60) -> str:
    """Return an ISO 8601 timestamp `seconds_ago` seconds in the past."""
    dt = datetime.now(tz=timezone.utc) - timedelta(seconds=seconds_ago)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _old_timestamp(seconds_ago: int = 7200) -> str:
    """Return an ISO 8601 timestamp well beyond the default staleness threshold."""
    dt = datetime.now(tz=timezone.utc) - timedelta(seconds=seconds_ago)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class TestIsCopilotSessionActive:
    """Tests for the session detector function."""

    def _make_provider(self, events: list[IssueEvent]) -> MagicMock:
        provider = MagicMock()
        provider.list_pr_issue_events.return_value = events
        return provider

    def test_no_events_returns_false(self) -> None:
        provider = self._make_provider([])
        assert is_copilot_session_active(provider, 1) is False

    def test_started_without_terminal_recent_returns_true(self) -> None:
        """A recent start event with no terminal → active."""
        events = [IssueEvent(id=1, event="copilot_work_started", created_at=_recent_timestamp())]
        provider = self._make_provider(events)
        assert is_copilot_session_active(provider, 1) is True

    def test_started_with_finished_returns_false(self) -> None:
        events = [
            IssueEvent(id=1, event="copilot_work_started", created_at=_recent_timestamp()),
            IssueEvent(id=2, event="copilot_work_finished", created_at=_recent_timestamp(30)),
        ]
        provider = self._make_provider(events)
        assert is_copilot_session_active(provider, 1) is False

    def test_started_with_failure_returns_false(self) -> None:
        events = [
            IssueEvent(id=1, event="copilot_work_started", created_at=_recent_timestamp()),
            IssueEvent(id=2, event="copilot_work_finished_failure", created_at=_recent_timestamp(30)),
        ]
        provider = self._make_provider(events)
        assert is_copilot_session_active(provider, 1) is False

    def test_multiple_sessions_latest_active(self) -> None:
        """When the latest start has no terminal and is recent, session is active."""
        events = [
            IssueEvent(id=1, event="copilot_work_started", created_at=_recent_timestamp(300)),
            IssueEvent(id=2, event="copilot_work_finished", created_at=_recent_timestamp(200)),
            IssueEvent(id=3, event="copilot_work_started", created_at=_recent_timestamp(60)),
        ]
        provider = self._make_provider(events)
        assert is_copilot_session_active(provider, 1) is True

    def test_multiple_sessions_latest_finished(self) -> None:
        """When the latest start has a terminal, session is not active."""
        events = [
            IssueEvent(id=1, event="copilot_work_started", created_at=_recent_timestamp(300)),
            IssueEvent(id=2, event="copilot_work_finished", created_at=_recent_timestamp(200)),
            IssueEvent(id=3, event="copilot_work_started", created_at=_recent_timestamp(100)),
            IssueEvent(id=4, event="copilot_work_finished", created_at=_recent_timestamp(50)),
        ]
        provider = self._make_provider(events)
        assert is_copilot_session_active(provider, 1) is False

    def test_api_failure_returns_true(self) -> None:
        """When API call fails, assume active session (fail-closed)."""
        provider = MagicMock()
        provider.list_pr_issue_events.side_effect = RuntimeError("API error")
        assert is_copilot_session_active(provider, 1) is True

    def test_stale_session_returns_false(self) -> None:
        """A start event older than the staleness threshold with no terminal → inactive."""
        events = [IssueEvent(id=1, event="copilot_work_started", created_at=_old_timestamp())]
        provider = self._make_provider(events)
        assert is_copilot_session_active(provider, 1) is False

    def test_stale_session_custom_threshold_via_env(self) -> None:
        """AGDT_MAX_SESSION_AGE_SECONDS env var overrides default threshold."""
        # Use a 10-second threshold; event is 60 seconds old → stale
        events = [IssueEvent(id=1, event="copilot_work_started", created_at=_recent_timestamp(60))]
        provider = self._make_provider(events)
        with patch.dict("os.environ", {"AGDT_MAX_SESSION_AGE_SECONDS": "10"}):
            assert is_copilot_session_active(provider, 1) is False

    def test_unparseable_created_at_falls_back_to_active(self) -> None:
        """If created_at cannot be parsed, treat session as potentially active."""
        events = [IssueEvent(id=1, event="copilot_work_started", created_at="not-a-date")]
        provider = self._make_provider(events)
        assert is_copilot_session_active(provider, 1) is True

    def test_empty_created_at_falls_back_to_active(self) -> None:
        """If created_at is empty string, treat session as potentially active."""
        events = [IssueEvent(id=1, event="copilot_work_started", created_at="")]
        provider = self._make_provider(events)
        assert is_copilot_session_active(provider, 1) is True


class TestIsSessionStale:
    """Tests for the _is_session_stale helper."""

    def test_old_timestamp_is_stale(self) -> None:
        assert _is_session_stale(_old_timestamp(), _DEFAULT_MAX_SESSION_AGE_SECONDS) is True

    def test_recent_timestamp_is_not_stale(self) -> None:
        assert _is_session_stale(_recent_timestamp(), _DEFAULT_MAX_SESSION_AGE_SECONDS) is False

    def test_invalid_timestamp_is_not_stale(self) -> None:
        """Unparseable timestamps are conservatively treated as not stale."""
        assert _is_session_stale("garbage", 3600) is False

    def test_empty_string_is_not_stale(self) -> None:
        assert _is_session_stale("", 3600) is False

    def test_naive_datetime_is_handled(self) -> None:
        """Naive datetime (no timezone) is normalized to UTC without raising TypeError."""
        # A naive ISO timestamp (no offset, no Z) — e.g. from a misconfigured source
        naive_old = (datetime.now(tz=timezone.utc) - timedelta(seconds=7200)).strftime("%Y-%m-%dT%H:%M:%S")
        assert _is_session_stale(naive_old, 3600) is True

        naive_recent = (datetime.now(tz=timezone.utc) - timedelta(seconds=30)).strftime("%Y-%m-%dT%H:%M:%S")
        assert _is_session_stale(naive_recent, 3600) is False


class TestGetMaxSessionAgeSeconds:
    """Tests for the _get_max_session_age_seconds helper."""

    def test_default_when_env_not_set(self) -> None:
        with patch.dict("os.environ", {}, clear=False):
            os.environ.pop("AGDT_MAX_SESSION_AGE_SECONDS", None)
            from agentic_devtools.cli.ci.pipeline.session_detector import (
                _get_max_session_age_seconds,
            )

            assert _get_max_session_age_seconds() == _DEFAULT_MAX_SESSION_AGE_SECONDS

    def test_valid_positive_value(self) -> None:
        from agentic_devtools.cli.ci.pipeline.session_detector import (
            _get_max_session_age_seconds,
        )

        with patch.dict("os.environ", {"AGDT_MAX_SESSION_AGE_SECONDS": "1800"}):
            assert _get_max_session_age_seconds() == 1800

    def test_invalid_non_integer_falls_back_to_default(self) -> None:
        from agentic_devtools.cli.ci.pipeline.session_detector import (
            _get_max_session_age_seconds,
        )

        with patch.dict("os.environ", {"AGDT_MAX_SESSION_AGE_SECONDS": "not-a-number"}):
            assert _get_max_session_age_seconds() == _DEFAULT_MAX_SESSION_AGE_SECONDS

    def test_zero_falls_back_to_default(self) -> None:
        from agentic_devtools.cli.ci.pipeline.session_detector import (
            _get_max_session_age_seconds,
        )

        with patch.dict("os.environ", {"AGDT_MAX_SESSION_AGE_SECONDS": "0"}):
            assert _get_max_session_age_seconds() == _DEFAULT_MAX_SESSION_AGE_SECONDS

    def test_negative_falls_back_to_default(self) -> None:
        from agentic_devtools.cli.ci.pipeline.session_detector import (
            _get_max_session_age_seconds,
        )

        with patch.dict("os.environ", {"AGDT_MAX_SESSION_AGE_SECONDS": "-100"}):
            assert _get_max_session_age_seconds() == _DEFAULT_MAX_SESSION_AGE_SECONDS
