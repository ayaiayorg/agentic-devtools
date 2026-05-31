"""Tests for is_review_completion."""

from agentic_devtools.cli.ci.tracker.merger import is_review_completion
from agentic_devtools.cli.ci.tracker.models import DetectionSource, TrackedSession


class TestIsReviewCompletion:
    """Tests for is_review_completion function."""

    def test_reviews_api_source_is_review(self) -> None:
        session = TrackedSession(
            session_id="review-1",
            sources=[DetectionSource.REVIEWS_API],
            status="completed",
        )
        assert is_review_completion(session) is True

    def test_agent_task_source_is_not_review(self) -> None:
        session = TrackedSession(
            session_id="task-1",
            sources=[DetectionSource.AGENT_TASK],
            status="completed",
        )
        assert is_review_completion(session) is False

    def test_events_api_source_is_not_review(self) -> None:
        session = TrackedSession(
            session_id="event-1",
            sources=[DetectionSource.EVENTS_API],
            status="copilot_work_finished",
        )
        assert is_review_completion(session) is False

    def test_multi_source_with_reviews_is_review(self) -> None:
        session = TrackedSession(
            session_id="mixed-1",
            sources=[DetectionSource.AGENT_TASK, DetectionSource.REVIEWS_API],
            status="completed",
        )
        assert is_review_completion(session) is True

    def test_empty_sources(self) -> None:
        session = TrackedSession(session_id="empty-1", sources=[])
        assert is_review_completion(session) is False
