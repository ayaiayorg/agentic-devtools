"""Tests for CommentInfo dataclass."""

from agentic_devtools.cli.ci.evaluator.models import CommentInfo


class TestCommentInfo:
    """Tests for CommentInfo frozen dataclass."""

    def test_default_values(self):
        """CommentInfo has sensible defaults."""
        c = CommentInfo(id=1)
        assert c.id == 1
        assert c.author == ""
        assert c.body == ""
        assert c.created_at == ""

    def test_with_all_fields(self):
        """CommentInfo stores all fields."""
        c = CommentInfo(id=1, author="copilot[bot]", body="Done!", created_at="2024-01-01T00:00:00Z")
        assert c.author == "copilot[bot]"
        assert c.body == "Done!"
        assert c.created_at == "2024-01-01T00:00:00Z"

    def test_frozen(self):
        """CommentInfo is immutable."""
        c = CommentInfo(id=1)
        try:
            c.id = 2  # type: ignore[misc]
            assert False, "Should raise"
        except AttributeError:
            pass
