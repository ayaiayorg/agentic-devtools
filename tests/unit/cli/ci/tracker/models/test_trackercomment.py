"""Tests for TrackerComment dataclass."""

from agentic_devtools.cli.ci.tracker.models import (
    DetectionSource,
    TrackedSession,
    TrackerComment,
)


class TestTrackerComment:
    """Tests for TrackerComment construction and session list management."""

    def test_default_fields(self) -> None:
        comment = TrackerComment()
        assert comment.comment_id is None
        assert comment.pr_number == 0
        assert comment.last_checked == ""
        assert comment.sessions == []
        assert comment.raw_body == ""

    def test_with_sessions(self) -> None:
        sessions = [
            TrackedSession(session_id="s1", status="completed"),
            TrackedSession(session_id="s2", status="running"),
        ]
        comment = TrackerComment(
            comment_id=12345,
            pr_number=42,
            last_checked="2026-05-29T08:00:00Z",
            sessions=sessions,
        )
        assert comment.comment_id == 12345
        assert len(comment.sessions) == 2
        assert comment.sessions[0].session_id == "s1"

    def test_to_dict(self) -> None:
        comment = TrackerComment(
            comment_id=100,
            pr_number=7,
            last_checked="2026-05-29T10:00:00Z",
            sessions=[
                TrackedSession(
                    session_id="t1",
                    sources=[DetectionSource.AGENT_TASK],
                    status="completed",
                )
            ],
        )
        d = comment.to_dict()
        assert d["comment_id"] == 100
        assert d["pr_number"] == 7
        assert len(d["sessions"]) == 1
        assert d["sessions"][0]["session_id"] == "t1"

    def test_from_dict(self) -> None:
        data = {
            "comment_id": 200,
            "pr_number": 15,
            "last_checked": "2026-05-29T11:00:00Z",
            "sessions": [
                {
                    "session_id": "t2",
                    "sources": ["reviews-api"],
                    "status": "completed",
                    "detected_at": "2026-05-29T11:00:00Z",
                    "dispatch_run_url": "",
                    "pr_number": 15,
                    "correlation_id": "",
                }
            ],
        }
        comment = TrackerComment.from_dict(data)
        assert comment.comment_id == 200
        assert len(comment.sessions) == 1
        assert comment.sessions[0].sources == [DetectionSource.REVIEWS_API]

    def test_roundtrip_serialization(self) -> None:
        original = TrackerComment(
            comment_id=300,
            pr_number=99,
            last_checked="2026-05-29T12:00:00Z",
            sessions=[
                TrackedSession(
                    session_id="rt-1",
                    sources=[DetectionSource.AGENT_TASK, DetectionSource.EVENTS_API],
                    status="completed",
                    detected_at="2026-05-29T12:00:00Z",
                )
            ],
        )
        restored = TrackerComment.from_dict(original.to_dict())
        assert restored.comment_id == original.comment_id
        assert restored.pr_number == original.pr_number
        assert restored.last_checked == original.last_checked
        assert len(restored.sessions) == 1
        assert restored.sessions[0].session_id == "rt-1"
