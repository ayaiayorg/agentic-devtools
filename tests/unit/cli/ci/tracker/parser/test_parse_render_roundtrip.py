"""Tests for parser/renderer round-trip losslessness."""

from agentic_devtools.cli.ci.tracker.models import (
    DetectionSource,
    TrackedSession,
    TrackerComment,
)
from agentic_devtools.cli.ci.tracker.parser import parse_tracker_comment
from agentic_devtools.cli.ci.tracker.renderer import render_tracker_comment


class TestParseRenderRoundtrip:
    """Tests verifying parse → render → parse produces consistent results."""

    def test_single_session_roundtrip(self) -> None:
        original = TrackerComment(
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
        rendered = render_tracker_comment(original)
        parsed = parse_tracker_comment(rendered)

        assert parsed.last_checked == original.last_checked
        assert parsed.pr_number == original.pr_number
        assert len(parsed.sessions) == 1
        assert parsed.sessions[0].session_id == "task-123"
        assert parsed.sessions[0].sources == [DetectionSource.AGENT_TASK]
        assert parsed.sessions[0].status == "completed"
        assert parsed.sessions[0].dispatch_run_url == "https://example.com/run/1"

    def test_multiple_sessions_roundtrip(self) -> None:
        original = TrackerComment(
            pr_number=10,
            last_checked="2026-05-29T10:00:00Z",
            sessions=[
                TrackedSession(
                    session_id="running-1",
                    sources=[DetectionSource.AGENT_TASK],
                    status="running",
                    detected_at="2026-05-29T09:50:00Z",
                ),
                TrackedSession(
                    session_id="task-456",
                    sources=[DetectionSource.EVENTS_API],
                    status="copilot_work_finished",
                    detected_at="2026-05-29T09:00:00Z",
                    dispatch_run_url="https://example.com/run/2",
                ),
            ],
        )
        rendered = render_tracker_comment(original)
        parsed = parse_tracker_comment(rendered)

        assert len(parsed.sessions) == 2
        # Running should be first
        assert parsed.sessions[0].session_id == "running-1"
        assert parsed.sessions[0].status == "running"
        assert parsed.sessions[1].session_id == "task-456"

    def test_multi_source_session_roundtrip(self) -> None:
        """Verify that sessions with multiple sources survive parse → render → parse."""
        original = TrackerComment(
            pr_number=99,
            last_checked="2026-05-29T12:00:00Z",
            sessions=[
                TrackedSession(
                    session_id="task-789",
                    sources=[DetectionSource.AGENT_TASK, DetectionSource.EVENTS_API],
                    status="completed",
                    detected_at="2026-05-29T11:30:00Z",
                    dispatch_run_url="https://example.com/run/3",
                ),
                TrackedSession(
                    session_id="review-100",
                    sources=[DetectionSource.REVIEWS_API, DetectionSource.EVENTS_API],
                    status="completed",
                    detected_at="2026-05-29T11:00:00Z",
                ),
            ],
        )
        rendered = render_tracker_comment(original)
        parsed = parse_tracker_comment(rendered)

        assert len(parsed.sessions) == 2
        # First session should retain both sources
        task_session = next(s for s in parsed.sessions if s.session_id == "task-789")
        assert DetectionSource.AGENT_TASK in task_session.sources
        assert DetectionSource.EVENTS_API in task_session.sources
        assert len(task_session.sources) == 2
        # Second session should retain both sources
        review_session = next(s for s in parsed.sessions if s.session_id == "review-100")
        assert DetectionSource.REVIEWS_API in review_session.sources
        assert DetectionSource.EVENTS_API in review_session.sources
        assert len(review_session.sources) == 2

    def test_empty_sessions_roundtrip(self) -> None:
        """Verify that a tracker comment with no sessions survives round-trip."""
        original = TrackerComment(
            pr_number=1,
            last_checked="2026-05-29T11:00:00Z",
            sessions=[],
        )
        rendered = render_tracker_comment(original)
        parsed = parse_tracker_comment(rendered)

        assert parsed.pr_number == 1
        assert parsed.last_checked == "2026-05-29T11:00:00Z"
        assert parsed.sessions == []
