"""Tests for tracker comment renderer."""

from agentic_devtools.cli.ci.tracker.models import (
    DetectionSource,
    TrackedSession,
    TrackerComment,
)
from agentic_devtools.cli.ci.tracker.renderer import render_tracker_comment


class TestRenderTrackerComment:
    """Tests for render_tracker_comment."""

    def test_basic_render(self) -> None:
        comment = TrackerComment(
            pr_number=42,
            last_checked="2026-05-29T08:00:00Z",
            sessions=[
                TrackedSession(
                    session_id="task-123",
                    sources=[DetectionSource.AGENT_TASK],
                    status="completed",
                    detected_at="2026-05-29T07:15:00Z",
                    dispatch_run_url="https://example.com/run/1",
                )
            ],
        )
        result = render_tracker_comment(comment)
        assert "<!-- agent-session-tracker" in result
        assert "last_checked=2026-05-29T08:00:00Z" in result
        assert "## Agent Sessions for PR #42" in result
        assert "task-123" in result
        assert "agent-task" in result
        assert "completed" in result
        assert "[run](https://example.com/run/1)" in result

    def test_multi_source_session(self) -> None:
        comment = TrackerComment(
            pr_number=10,
            last_checked="2026-05-29T09:00:00Z",
            sessions=[
                TrackedSession(
                    session_id="task-456",
                    sources=[DetectionSource.AGENT_TASK, DetectionSource.EVENTS_API],
                    status="completed",
                    detected_at="2026-05-29T08:00:00Z",
                )
            ],
        )
        result = render_tracker_comment(comment)
        assert "agent-task, events-api" in result

    def test_no_dispatch_url_renders_dash(self) -> None:
        comment = TrackerComment(
            pr_number=5,
            last_checked="2026-05-29T09:00:00Z",
            sessions=[
                TrackedSession(
                    session_id="task-789",
                    sources=[DetectionSource.AGENT_TASK],
                    status="running",
                    detected_at="2026-05-29T08:50:00Z",
                )
            ],
        )
        result = render_tracker_comment(comment)
        # The dispatch column should have a dash
        lines = result.split("\n")
        session_line = [line for line in lines if "task-789" in line][0]
        assert "| — |" in session_line

    def test_running_sessions_sorted_first(self) -> None:
        comment = TrackerComment(
            pr_number=3,
            last_checked="2026-05-29T09:00:00Z",
            sessions=[
                TrackedSession(
                    session_id="completed-1",
                    sources=[DetectionSource.EVENTS_API],
                    status="completed",
                    detected_at="2026-05-29T08:00:00Z",
                ),
                TrackedSession(
                    session_id="running-1",
                    sources=[DetectionSource.AGENT_TASK],
                    status="running",
                    detected_at="2026-05-29T08:30:00Z",
                ),
            ],
        )
        result = render_tracker_comment(comment)
        lines = [
            line
            for line in result.split("\n")
            if line.startswith("| ") and "Session ID" not in line and "---" not in line
        ]
        assert "running-1" in lines[0]
        assert "completed-1" in lines[1]

    def test_contains_html_comment_header(self) -> None:
        comment = TrackerComment(
            pr_number=1,
            last_checked="2026-05-29T10:00:00Z",
            sessions=[],
        )
        result = render_tracker_comment(comment)
        assert result.startswith("<!-- agent-session-tracker\n")
        assert "-->" in result
