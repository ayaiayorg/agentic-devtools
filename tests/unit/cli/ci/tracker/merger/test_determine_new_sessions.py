"""Tests for determine_new_sessions."""

from agentic_devtools.cli.ci.tracker.merger import determine_new_sessions
from agentic_devtools.cli.ci.tracker.models import DetectionSource, TrackedSession


class TestDetermineNewSessions:
    """Tests for determine_new_sessions dispatch logic."""

    def test_new_completed_session_needs_dispatch(self) -> None:
        existing: list[TrackedSession] = []
        merged = [
            TrackedSession(
                session_id="task-1",
                sources=[DetectionSource.AGENT_TASK],
                status="completed",
                detected_at="2026-05-29T07:15:00Z",
            )
        ]
        result = determine_new_sessions(existing, merged)
        assert len(result) == 1
        assert result[0].session_id == "task-1"

    def test_existing_session_not_dispatched(self) -> None:
        existing = [
            TrackedSession(
                session_id="task-1",
                sources=[DetectionSource.AGENT_TASK],
                status="completed",
            )
        ]
        merged = [
            TrackedSession(
                session_id="task-1",
                sources=[DetectionSource.AGENT_TASK],
                status="completed",
            )
        ]
        result = determine_new_sessions(existing, merged)
        assert len(result) == 0

    def test_running_session_not_dispatched(self) -> None:
        existing: list[TrackedSession] = []
        merged = [
            TrackedSession(
                session_id="task-2",
                sources=[DetectionSource.AGENT_TASK],
                status="running",
            )
        ]
        result = determine_new_sessions(existing, merged)
        assert len(result) == 0

    def test_session_with_dispatch_url_not_dispatched(self) -> None:
        existing: list[TrackedSession] = []
        merged = [
            TrackedSession(
                session_id="task-3",
                sources=[DetectionSource.AGENT_TASK],
                status="completed",
                dispatch_run_url="https://example.com/run/1",
            )
        ]
        result = determine_new_sessions(existing, merged)
        assert len(result) == 0

    def test_cold_start_reconstruction(self) -> None:
        """When existing comment has sessions, only new ones get dispatched."""
        existing = [
            TrackedSession(session_id="old-1", status="completed"),
            TrackedSession(session_id="old-2", status="completed"),
        ]
        merged = [
            TrackedSession(session_id="old-1", status="completed"),
            TrackedSession(session_id="old-2", status="completed"),
            TrackedSession(
                session_id="new-1",
                sources=[DetectionSource.EVENTS_API],
                status="copilot_work_finished",
                detected_at="2026-05-29T09:00:00Z",
            ),
        ]
        result = determine_new_sessions(existing, merged)
        assert len(result) == 1
        assert result[0].session_id == "new-1"
