"""Tests for SkippedFile dataclass."""

from agentic_devtools.cli.azure_devops.review_state import SkippedFile


class TestSkippedFile:
    """Tests for SkippedFile dataclass."""

    def test_creation(self):
        """Test basic creation with path and reason."""
        sf = SkippedFile(path="/src/file.ts", reason="not_on_branch")
        assert sf.path == "/src/file.ts"
        assert sf.reason == "not_on_branch"

    def test_to_dict(self):
        """Test serialization to dictionary."""
        sf = SkippedFile(path="/src/file.ts", reason="already_reviewed")
        d = sf.to_dict()
        assert d == {"path": "/src/file.ts", "reason": "already_reviewed"}

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {"path": "/src/file.ts", "reason": "not_on_branch"}
        sf = SkippedFile.from_dict(data)
        assert sf.path == "/src/file.ts"
        assert sf.reason == "not_on_branch"

    def test_roundtrip(self):
        """Test to_dict/from_dict round-trips correctly."""
        original = SkippedFile(path="/lib/util.py", reason="already_reviewed")
        restored = SkippedFile.from_dict(original.to_dict())
        assert restored.path == original.path
        assert restored.reason == original.reason
