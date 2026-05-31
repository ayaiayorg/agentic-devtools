"""Tests for session merger."""

from agentic_devtools.cli.ci.tracker.merger import merge_sessions
from agentic_devtools.cli.ci.tracker.models import DetectionSource, TrackedSession


class TestMergeSessions:
    """Tests for merge_sessions deduplication and correlation."""

    def test_dedup_by_task_id(self) -> None:
        existing = [
            TrackedSession(
                session_id="task-123",
                sources=[DetectionSource.AGENT_TASK],
                status="completed",
                detected_at="2026-05-29T07:15:00Z",
            )
        ]
        new_events = [
            TrackedSession(
                session_id="task-123",
                sources=[DetectionSource.EVENTS_API],
                status="copilot_work_finished",
                detected_at="2026-05-29T07:15:30Z",
            )
        ]
        result = merge_sessions(existing, new_events_api=new_events)
        assert len(result) == 1
        assert DetectionSource.AGENT_TASK in result[0].sources
        assert DetectionSource.EVENTS_API in result[0].sources

    def test_timestamp_fallback_correlation(self) -> None:
        existing = [
            TrackedSession(
                session_id="task-100",
                sources=[DetectionSource.AGENT_TASK],
                status="completed",
                detected_at="2026-05-29T07:15:00Z",
            )
        ]
        # Different ID but within 60s window
        new_events = [
            TrackedSession(
                session_id="event-200",
                sources=[DetectionSource.EVENTS_API],
                status="copilot_work_finished",
                detected_at="2026-05-29T07:15:30Z",
            )
        ]
        result = merge_sessions(existing, new_events_api=new_events)
        assert len(result) == 1
        assert result[0].session_id == "task-100"
        assert DetectionSource.EVENTS_API in result[0].sources

    def test_no_correlation_beyond_window(self) -> None:
        existing = [
            TrackedSession(
                session_id="task-100",
                sources=[DetectionSource.AGENT_TASK],
                status="completed",
                detected_at="2026-05-29T07:15:00Z",
            )
        ]
        # More than 60 seconds apart
        new_events = [
            TrackedSession(
                session_id="event-300",
                sources=[DetectionSource.EVENTS_API],
                status="copilot_work_finished",
                detected_at="2026-05-29T07:20:00Z",
            )
        ]
        result = merge_sessions(existing, new_events_api=new_events)
        assert len(result) == 2

    def test_empty_existing(self) -> None:
        new_tasks = [
            TrackedSession(
                session_id="task-1",
                sources=[DetectionSource.AGENT_TASK],
                status="completed",
                detected_at="2026-05-29T07:15:00Z",
            )
        ]
        result = merge_sessions([], new_agent_task=new_tasks)
        assert len(result) == 1
        assert result[0].session_id == "task-1"

    def test_multiple_sources_merged(self) -> None:
        result = merge_sessions(
            [],
            new_agent_task=[
                TrackedSession(
                    session_id="task-50",
                    sources=[DetectionSource.AGENT_TASK],
                    status="completed",
                    detected_at="2026-05-29T07:00:00Z",
                )
            ],
            new_events_api=[
                TrackedSession(
                    session_id="event-60",
                    sources=[DetectionSource.EVENTS_API],
                    status="copilot_work_finished",
                    detected_at="2026-05-29T08:00:00Z",
                )
            ],
            new_reviews_api=[
                TrackedSession(
                    session_id="review-70",
                    sources=[DetectionSource.REVIEWS_API],
                    status="completed",
                    detected_at="2026-05-29T09:00:00Z",
                )
            ],
        )
        assert len(result) == 3

    def test_duplicate_source_not_added_tier1(self) -> None:
        """Source already in combined_sources is not duplicated (tier-1 exact match)."""
        existing = [
            TrackedSession(
                session_id="task-123",
                sources=[DetectionSource.AGENT_TASK, DetectionSource.EVENTS_API],
                status="completed",
                detected_at="2026-05-29T07:15:00Z",
            )
        ]
        # New session has same ID and one source that already exists
        new_events = [
            TrackedSession(
                session_id="task-123",
                sources=[DetectionSource.AGENT_TASK],
                status="completed",
                detected_at="2026-05-29T07:15:30Z",
            )
        ]
        result = merge_sessions(existing, new_events_api=new_events)
        assert len(result) == 1
        # AGENT_TASK should not be duplicated
        assert result[0].sources.count(DetectionSource.AGENT_TASK) == 1

    def test_duplicate_source_not_added_tier2(self) -> None:
        """Source already in combined_sources is not duplicated (tier-2 timestamp correlation)."""
        existing = [
            TrackedSession(
                session_id="task-100",
                sources=[DetectionSource.AGENT_TASK],
                status="completed",
                detected_at="2026-05-29T07:15:00Z",
            )
        ]
        # Different ID, within 60s window, same source (AGENT_TASK already in existing)
        new_events = [
            TrackedSession(
                session_id="event-200",
                sources=[DetectionSource.AGENT_TASK],
                status="completed",
                detected_at="2026-05-29T07:15:30Z",
            )
        ]
        result = merge_sessions(existing, new_events_api=new_events)
        assert len(result) == 1
        # AGENT_TASK should not be duplicated in the correlated session
        assert result[0].sources.count(DetectionSource.AGENT_TASK) == 1

    def test_new_session_no_detected_at_added_as_unique(self) -> None:
        """New session with no detected_at bypasses timestamp correlation and adds as new."""
        existing = [
            TrackedSession(
                session_id="task-100",
                sources=[DetectionSource.AGENT_TASK],
                status="completed",
                detected_at="2026-05-29T07:15:00Z",
            )
        ]
        new_events = [
            TrackedSession(
                session_id="event-no-ts",
                sources=[DetectionSource.EVENTS_API],
                status="completed",
                detected_at="",
            )
        ]
        result = merge_sessions(existing, new_events_api=new_events)
        assert len(result) == 2

    def test_new_session_invalid_timestamp_added_as_unique(self) -> None:
        """New session with invalid timestamp bypasses correlation and adds as new."""
        existing = [
            TrackedSession(
                session_id="task-100",
                sources=[DetectionSource.AGENT_TASK],
                status="completed",
                detected_at="2026-05-29T07:15:00Z",
            )
        ]
        new_events = [
            TrackedSession(
                session_id="event-bad-ts",
                sources=[DetectionSource.EVENTS_API],
                status="completed",
                detected_at="not-a-valid-timestamp",
            )
        ]
        result = merge_sessions(existing, new_events_api=new_events)
        assert len(result) == 2

    def test_existing_session_no_detected_at_skipped_in_correlation(self) -> None:
        """Existing session with no detected_at is skipped during timestamp correlation."""
        existing = [
            TrackedSession(
                session_id="task-no-ts",
                sources=[DetectionSource.AGENT_TASK],
                status="completed",
                detected_at="",
            )
        ]
        # New session with valid timestamp - can't correlate against existing (no detected_at)
        new_events = [
            TrackedSession(
                session_id="event-200",
                sources=[DetectionSource.EVENTS_API],
                status="completed",
                detected_at="2026-05-29T07:15:30Z",
            )
        ]
        result = merge_sessions(existing, new_events_api=new_events)
        assert len(result) == 2

    def test_existing_session_invalid_timestamp_skipped_in_correlation(self) -> None:
        """Existing session with invalid timestamp is skipped during correlation."""
        existing = [
            TrackedSession(
                session_id="task-bad-ts",
                sources=[DetectionSource.AGENT_TASK],
                status="completed",
                detected_at="not-a-valid-timestamp",
            )
        ]
        new_events = [
            TrackedSession(
                session_id="event-200",
                sources=[DetectionSource.EVENTS_API],
                status="completed",
                detected_at="2026-05-29T07:15:30Z",
            )
        ]
        result = merge_sessions(existing, new_events_api=new_events)
        assert len(result) == 2

    def test_non_z_timestamps_correlate_correctly(self) -> None:
        """Timestamps in +00:00 offset format (no Z suffix) correlate within window."""
        existing = [
            TrackedSession(
                session_id="task-100",
                sources=[DetectionSource.AGENT_TASK],
                status="completed",
                detected_at="2026-05-29T07:15:00+00:00",
            )
        ]
        new_events = [
            TrackedSession(
                session_id="event-200",
                sources=[DetectionSource.EVENTS_API],
                status="completed",
                detected_at="2026-05-29T07:15:30+00:00",
            )
        ]
        result = merge_sessions(existing, new_events_api=new_events)
        assert len(result) == 1
        assert DetectionSource.EVENTS_API in result[0].sources
