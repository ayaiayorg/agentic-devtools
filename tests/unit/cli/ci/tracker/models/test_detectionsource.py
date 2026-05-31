"""Tests for DetectionSource enum."""

from agentic_devtools.cli.ci.tracker.models import DetectionSource


class TestDetectionSource:
    """Tests for DetectionSource enum values and rendering."""

    def test_agent_task_value(self) -> None:
        assert DetectionSource.AGENT_TASK.value == "agent-task"

    def test_events_api_value(self) -> None:
        assert DetectionSource.EVENTS_API.value == "events-api"

    def test_reviews_api_value(self) -> None:
        assert DetectionSource.REVIEWS_API.value == "reviews-api"

    def test_str_rendering(self) -> None:
        assert str(DetectionSource.AGENT_TASK) == "agent-task"
        assert str(DetectionSource.EVENTS_API) == "events-api"
        assert str(DetectionSource.REVIEWS_API) == "reviews-api"

    def test_from_value(self) -> None:
        assert DetectionSource("agent-task") == DetectionSource.AGENT_TASK
        assert DetectionSource("events-api") == DetectionSource.EVENTS_API
        assert DetectionSource("reviews-api") == DetectionSource.REVIEWS_API
