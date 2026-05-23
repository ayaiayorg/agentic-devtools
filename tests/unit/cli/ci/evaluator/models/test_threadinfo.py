"""Tests for ThreadInfo dataclass."""

from agentic_devtools.cli.ci.evaluator.models import ThreadInfo


class TestThreadInfo:
    """Tests for ThreadInfo frozen dataclass."""

    def test_default_values(self):
        """ThreadInfo has sensible defaults."""
        t = ThreadInfo(comment_id=42)
        assert t.comment_id == 42
        assert t.path == ""
        assert t.start_line is None
        assert t.end_line is None
        assert t.is_resolved is False
        assert t.has_reply is False
        assert t.body == ""

    def test_with_all_fields(self):
        """ThreadInfo stores all fields."""
        t = ThreadInfo(
            comment_id=1,
            path="src/file.py",
            start_line=10,
            end_line=15,
            is_resolved=True,
            has_reply=True,
            body="Fix this",
        )
        assert t.path == "src/file.py"
        assert t.start_line == 10
        assert t.end_line == 15
        assert t.is_resolved is True
        assert t.has_reply is True

    def test_frozen(self):
        """ThreadInfo is immutable."""
        t = ThreadInfo(comment_id=1)
        try:
            t.comment_id = 2  # type: ignore[misc]
            assert False, "Should raise"
        except AttributeError:
            pass
