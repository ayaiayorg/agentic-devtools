"""Tests for TrackedSession dataclass."""

from agentic_devtools.cli.ci.tracker.models import DetectionSource, TrackedSession


class TestTrackedSession:
    """Tests for TrackedSession field defaults and serialization."""

    def test_default_fields(self) -> None:
        session = TrackedSession(session_id="task-123")
        assert session.session_id == "task-123"
        assert session.sources == []
        assert session.status == ""
        assert session.detected_at == ""
        assert session.dispatch_run_url == ""
        assert session.pr_number == 0
        assert session.correlation_id == ""

    def test_with_all_fields(self) -> None:
        session = TrackedSession(
            session_id="task-456",
            sources=[DetectionSource.AGENT_TASK, DetectionSource.EVENTS_API],
            status="completed",
            detected_at="2026-05-29T07:15:00Z",
            dispatch_run_url="https://github.com/org/repo/actions/runs/123",
            pr_number=42,
            correlation_id="event-789",
        )
        assert session.session_id == "task-456"
        assert len(session.sources) == 2
        assert session.pr_number == 42

    def test_to_dict(self) -> None:
        session = TrackedSession(
            session_id="task-123",
            sources=[DetectionSource.AGENT_TASK],
            status="completed",
            detected_at="2026-05-29T07:15:00Z",
            pr_number=10,
        )
        d = session.to_dict()
        assert d["session_id"] == "task-123"
        assert d["sources"] == ["agent-task"]
        assert d["status"] == "completed"
        assert d["pr_number"] == 10

    def test_from_dict(self) -> None:
        data = {
            "session_id": "task-999",
            "sources": ["events-api"],
            "status": "copilot_work_finished",
            "detected_at": "2026-05-29T08:00:00Z",
            "dispatch_run_url": "",
            "pr_number": 5,
            "correlation_id": "",
        }
        session = TrackedSession.from_dict(data)
        assert session.session_id == "task-999"
        assert session.sources == [DetectionSource.EVENTS_API]
        assert session.status == "copilot_work_finished"

    def test_roundtrip_serialization(self) -> None:
        original = TrackedSession(
            session_id="task-rt",
            sources=[DetectionSource.REVIEWS_API],
            status="completed",
            detected_at="2026-05-29T09:00:00Z",
            dispatch_run_url="https://example.com/run/1",
            pr_number=77,
            correlation_id="corr-1",
        )
        restored = TrackedSession.from_dict(original.to_dict())
        assert restored.session_id == original.session_id
        assert restored.sources == original.sources
        assert restored.status == original.status
        assert restored.detected_at == original.detected_at
        assert restored.dispatch_run_url == original.dispatch_run_url
        assert restored.pr_number == original.pr_number
        assert restored.correlation_id == original.correlation_id
