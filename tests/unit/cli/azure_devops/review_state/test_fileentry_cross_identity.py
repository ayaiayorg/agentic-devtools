"""Tests for FileEntry.crossIdentity field serialization/deserialization."""

from agentic_devtools.cli.azure_devops.review_state import FileEntry, ReviewStatus


class TestFileEntryCrossIdentity:
    """Tests for crossIdentity field on FileEntry."""

    def test_default_cross_identity_is_false(self):
        """FileEntry.crossIdentity defaults to False."""
        entry = FileEntry(
            threadId=1,
            commentId=2,
            folder="/src",
            fileName="a.ts",
        )
        assert entry.crossIdentity is False

    def test_cross_identity_true_serialization(self):
        """crossIdentity=True is included in to_dict output."""
        entry = FileEntry(
            threadId=1,
            commentId=2,
            folder="/src",
            fileName="a.ts",
            crossIdentity=True,
        )
        data = entry.to_dict()
        assert data["crossIdentity"] is True

    def test_cross_identity_false_not_serialized(self):
        """crossIdentity=False is not included in to_dict output (sparse)."""
        entry = FileEntry(
            threadId=1,
            commentId=2,
            folder="/src",
            fileName="a.ts",
            crossIdentity=False,
        )
        data = entry.to_dict()
        assert "crossIdentity" not in data

    def test_from_dict_with_cross_identity_true(self):
        """from_dict correctly reads crossIdentity=True."""
        data = {
            "threadId": 10,
            "commentId": 20,
            "folder": "/src",
            "fileName": "b.ts",
            "status": ReviewStatus.UNREVIEWED.value,
            "crossIdentity": True,
        }
        entry = FileEntry.from_dict(data)
        assert entry.crossIdentity is True

    def test_from_dict_without_cross_identity(self):
        """from_dict defaults crossIdentity to False when field is missing (backward compat)."""
        data = {
            "threadId": 10,
            "commentId": 20,
            "folder": "/src",
            "fileName": "b.ts",
            "status": ReviewStatus.UNREVIEWED.value,
        }
        entry = FileEntry.from_dict(data)
        assert entry.crossIdentity is False

    def test_roundtrip_cross_identity_true(self):
        """Serialize then deserialize preserves crossIdentity=True."""
        entry = FileEntry(
            threadId=1,
            commentId=2,
            folder="/src",
            fileName="a.ts",
            crossIdentity=True,
        )
        restored = FileEntry.from_dict(entry.to_dict())
        assert restored.crossIdentity is True

    def test_roundtrip_cross_identity_false(self):
        """Serialize then deserialize preserves crossIdentity=False."""
        entry = FileEntry(
            threadId=1,
            commentId=2,
            folder="/src",
            fileName="a.ts",
            crossIdentity=False,
        )
        restored = FileEntry.from_dict(entry.to_dict())
        assert restored.crossIdentity is False
