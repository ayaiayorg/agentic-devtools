"""Tests for session truncation logic."""

from agentic_devtools.cli.ci.tracker.models import DetectionSource, TrackedSession
from agentic_devtools.cli.ci.tracker.renderer import truncate_sessions


class TestTruncateSessions:
    """Tests for truncate_sessions preserving running and recent completed."""

    def test_preserves_all_running_sessions(self) -> None:
        sessions = [
            TrackedSession(
                session_id=f"running-{i}",
                sources=[DetectionSource.AGENT_TASK],
                status="running",
                detected_at=f"2026-05-29T0{i}:00:00Z",
            )
            for i in range(5)
        ]
        result = truncate_sessions(sessions)
        assert len(result) == 5
        assert all(s.status == "running" for s in result)

    def test_keeps_max_20_completed(self) -> None:
        sessions = [
            TrackedSession(
                session_id=f"completed-{i:03d}",
                sources=[DetectionSource.EVENTS_API],
                status="completed",
                detected_at=f"2026-05-{i + 1:02d}T08:00:00Z",
            )
            for i in range(30)
        ]
        result = truncate_sessions(sessions)
        completed = [s for s in result if s.status != "running"]
        assert len(completed) <= 20

    def test_most_recent_completed_kept(self) -> None:
        sessions = [
            TrackedSession(
                session_id=f"completed-{i:03d}",
                sources=[DetectionSource.EVENTS_API],
                status="completed",
                detected_at=f"2026-05-{i + 1:02d}T08:00:00Z",
            )
            for i in range(25)
        ]
        result = truncate_sessions(sessions)
        completed = [s for s in result if s.status != "running"]
        # Most recent should be kept (highest dates)
        ids = {s.session_id for s in completed}
        # The 20 most recent are completed-005 through completed-024 (dates 6th to 25th)
        assert "completed-024" in ids
        assert "completed-023" in ids

    def test_empty_list(self) -> None:
        result = truncate_sessions([])
        assert result == []

    def test_under_limit_unchanged(self) -> None:
        sessions = [
            TrackedSession(
                session_id="s1",
                sources=[DetectionSource.AGENT_TASK],
                status="completed",
                detected_at="2026-05-29T08:00:00Z",
            )
        ]
        result = truncate_sessions(sessions)
        assert len(result) == 1
        assert result[0].session_id == "s1"

    def test_truncates_further_when_rendered_exceeds_limit(self) -> None:
        """While loop trims completed sessions until the comment fits within the size limit."""
        from unittest.mock import patch

        sessions = [
            TrackedSession(
                session_id=f"completed-{i:03d}",
                sources=[DetectionSource.EVENTS_API],
                status="completed",
                detected_at=f"2026-05-{i + 1:02d}T08:00:00Z",
            )
            for i in range(25)
        ]
        # Use a tiny limit to force while-loop truncation after initial capping at 20
        with patch("agentic_devtools.cli.ci.tracker.renderer._MAX_COMMENT_CHARS", 200):
            result = truncate_sessions(sessions)
        # With only 200 chars allowed the while loop must have removed sessions
        assert len(result) < 20
