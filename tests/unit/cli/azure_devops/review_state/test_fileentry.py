"""Tests for FileEntry dataclass."""

from agentic_devtools.cli.azure_devops.review_state import FileEntry, ReviewStatus, SuggestionEntry


def _make_suggestion() -> SuggestionEntry:
    return SuggestionEntry(
        threadId=100,
        commentId=200,
        line=1,
        endLine=5,
        severity="high",
        outOfScope=False,
        linkText="lines 1 - 5",
        content="Missing null check",
    )


class TestFileEntry:
    """Tests for FileEntry dataclass."""

    def test_creation_with_defaults(self):
        """Test creation with minimal required fields and defaults."""
        f = FileEntry(threadId=161048, commentId=1771800050, folder="mgmt-backend", fileName="SomeFile.cs")
        assert f.threadId == 161048
        assert f.commentId == 1771800050
        assert f.folder == "mgmt-backend"
        assert f.fileName == "SomeFile.cs"
        assert f.status == ReviewStatus.UNREVIEWED
        assert f.summary is None
        assert f.changeTrackingId is None
        assert f.suggestions == []

    def test_creation_with_all_fields(self):
        """Test creation with all fields specified."""
        suggestion = _make_suggestion()
        f = FileEntry(
            threadId=1,
            commentId=2,
            folder="src",
            fileName="app.py",
            status="approved",
            summary="Looks good",
            changeTrackingId=42,
            suggestions=[suggestion],
        )
        assert f.status == "approved"
        assert f.summary == "Looks good"
        assert f.changeTrackingId == 42
        assert len(f.suggestions) == 1

    def test_to_dict(self):
        """Test serialization to dictionary."""
        f = FileEntry(
            threadId=161048,
            commentId=1771800050,
            folder="mgmt-backend",
            fileName="SomeFile.cs",
            status="unreviewed",
            summary=None,
            changeTrackingId=42,
            suggestions=[],
        )
        d = f.to_dict()
        assert d == {
            "threadId": 161048,
            "commentId": 1771800050,
            "folder": "mgmt-backend",
            "fileName": "SomeFile.cs",
            "status": "unreviewed",
            "summary": None,
            "changeTrackingId": 42,
            "suggestions": [],
        }

    def test_to_dict_with_suggestions(self):
        """Test serialization with suggestions."""
        suggestion = _make_suggestion()
        f = FileEntry(
            threadId=1,
            commentId=2,
            folder="src",
            fileName="app.py",
            suggestions=[suggestion],
        )
        d = f.to_dict()
        assert len(d["suggestions"]) == 1
        assert d["suggestions"][0]["threadId"] == 100

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "threadId": 161048,
            "commentId": 1771800050,
            "folder": "mgmt-backend",
            "fileName": "SomeFile.cs",
            "status": "approved",
            "summary": "Reviewed",
            "changeTrackingId": 42,
            "suggestions": [],
        }
        f = FileEntry.from_dict(data)
        assert f.threadId == 161048
        assert f.folder == "mgmt-backend"
        assert f.status == "approved"
        assert f.summary == "Reviewed"
        assert f.changeTrackingId == 42
        assert f.suggestions == []

    def test_from_dict_with_suggestions(self):
        """Test deserialization with embedded suggestions."""
        data = {
            "threadId": 1,
            "commentId": 2,
            "folder": "src",
            "fileName": "app.py",
            "suggestions": [
                {
                    "threadId": 100,
                    "commentId": 200,
                    "line": 1,
                    "endLine": 5,
                    "severity": "high",
                    "outOfScope": False,
                    "linkText": "lines 1 - 5",
                    "content": "Missing null check",
                }
            ],
        }
        f = FileEntry.from_dict(data)
        assert len(f.suggestions) == 1
        assert f.suggestions[0].threadId == 100

    def test_from_dict_defaults(self):
        """Test from_dict with missing optional fields uses defaults."""
        data = {"threadId": 1, "commentId": 2, "folder": "src", "fileName": "app.py"}
        f = FileEntry.from_dict(data)
        assert f.status == ReviewStatus.UNREVIEWED
        assert f.summary is None
        assert f.changeTrackingId is None
        assert f.suggestions == []

    def test_roundtrip(self):
        """Test to_dict/from_dict round-trips correctly."""
        suggestion = _make_suggestion()
        original = FileEntry(
            threadId=1,
            commentId=2,
            folder="src",
            fileName="app.py",
            status="needs-work",
            summary="Has issues",
            changeTrackingId=7,
            suggestions=[suggestion],
        )
        restored = FileEntry.from_dict(original.to_dict())
        assert restored.threadId == 1
        assert restored.status == "needs-work"
        assert restored.summary == "Has issues"
        assert restored.changeTrackingId == 7
        assert len(restored.suggestions) == 1

    def test_suggestions_default_is_independent(self):
        """Test that default suggestions lists are independent per instance."""
        f1 = FileEntry(threadId=1, commentId=1, folder="a", fileName="b.py")
        f2 = FileEntry(threadId=2, commentId=2, folder="a", fileName="c.py")
        f1.suggestions.append(_make_suggestion())
        assert f2.suggestions == []
