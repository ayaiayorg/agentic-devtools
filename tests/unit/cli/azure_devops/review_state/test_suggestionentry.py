"""Tests for SuggestionEntry dataclass."""

from agentic_devtools.cli.azure_devops.review_state import SuggestionEntry


def _make_suggestion(**kwargs) -> SuggestionEntry:
    defaults = {
        "threadId": 100,
        "commentId": 200,
        "line": 10,
        "endLine": 20,
        "severity": "high",
        "outOfScope": False,
        "linkText": "lines 10 - 20",
        "content": "Missing null check",
    }
    defaults.update(kwargs)
    return SuggestionEntry(**defaults)


class TestSuggestionEntry:
    """Tests for SuggestionEntry dataclass."""

    def test_creation(self):
        """Test basic creation of a SuggestionEntry."""
        s = _make_suggestion()
        assert s.threadId == 100
        assert s.commentId == 200
        assert s.line == 10
        assert s.endLine == 20
        assert s.severity == "high"
        assert s.outOfScope is False
        assert s.linkText == "lines 10 - 20"
        assert s.content == "Missing null check"

    def test_to_dict(self):
        """Test serialization to dictionary."""
        s = _make_suggestion()
        d = s.to_dict()
        assert d == {
            "threadId": 100,
            "commentId": 200,
            "line": 10,
            "endLine": 20,
            "severity": "high",
            "outOfScope": False,
            "linkText": "lines 10 - 20",
            "content": "Missing null check",
        }

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "threadId": 100,
            "commentId": 200,
            "line": 10,
            "endLine": 20,
            "severity": "high",
            "outOfScope": False,
            "linkText": "lines 10 - 20",
            "content": "Missing null check",
        }
        s = SuggestionEntry.from_dict(data)
        assert s.threadId == 100
        assert s.commentId == 200
        assert s.line == 10
        assert s.endLine == 20
        assert s.severity == "high"
        assert s.outOfScope is False
        assert s.linkText == "lines 10 - 20"
        assert s.content == "Missing null check"

    def test_roundtrip(self):
        """Test that to_dict/from_dict round-trips correctly."""
        original = _make_suggestion(outOfScope=True, severity="low")
        restored = SuggestionEntry.from_dict(original.to_dict())
        assert restored.threadId == original.threadId
        assert restored.outOfScope is True
        assert restored.severity == "low"

    def test_out_of_scope_true(self):
        """Test out_of_scope=True serializes correctly."""
        s = _make_suggestion(outOfScope=True)
        assert s.to_dict()["outOfScope"] is True
