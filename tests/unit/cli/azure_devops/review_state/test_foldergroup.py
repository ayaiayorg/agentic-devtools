"""Tests for FolderGroup dataclass."""

from agentic_devtools.cli.azure_devops.review_state import FolderGroup


class TestFolderGroup:
    """Tests for FolderGroup dataclass."""

    def test_creation_with_defaults(self):
        """Test creation with default files list."""
        f = FolderGroup()
        assert f.files == []

    def test_creation_with_files(self):
        """Test creation with explicit files list."""
        files = ["/mgmt-backend/SomeFile.cs", "/mgmt-backend/OtherFile.cs"]
        f = FolderGroup(files=files)
        assert f.files == files

    def test_to_dict(self):
        """Test serialization to dictionary."""
        files = ["/mgmt-backend/SomeFile.cs"]
        f = FolderGroup(files=files)
        d = f.to_dict()
        assert d == {
            "files": ["/mgmt-backend/SomeFile.cs"],
        }

    def test_to_dict_empty(self):
        """Test serialization of empty folder group."""
        f = FolderGroup()
        d = f.to_dict()
        assert d == {"files": []}

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "files": ["/mgmt-backend/SomeFile.cs"],
        }
        f = FolderGroup.from_dict(data)
        assert f.files == ["/mgmt-backend/SomeFile.cs"]

    def test_from_dict_defaults(self):
        """Test from_dict with missing optional fields uses defaults."""
        data = {}
        f = FolderGroup.from_dict(data)
        assert f.files == []

    def test_roundtrip(self):
        """Test to_dict/from_dict round-trips correctly."""
        original = FolderGroup(files=["/a/b.py", "/a/c.py"])
        restored = FolderGroup.from_dict(original.to_dict())
        assert restored.files == ["/a/b.py", "/a/c.py"]

    def test_files_default_is_independent(self):
        """Test that default files lists are independent per instance."""
        f1 = FolderGroup()
        f2 = FolderGroup()
        f1.files.append("/some/file.cs")
        assert f2.files == []

    def test_from_dict_normalizes_file_paths(self):
        """Test that from_dict normalizes file paths with leading slash."""
        data = {
            "files": ["mgmt-backend/SomeFile.cs", "/mgmt-backend/OtherFile.cs"],
        }
        f = FolderGroup.from_dict(data)
        assert f.files == ["/mgmt-backend/SomeFile.cs", "/mgmt-backend/OtherFile.cs"]

    def test_from_dict_ignores_legacy_thread_fields(self):
        """Test that from_dict ignores old threadId/commentId/status fields."""
        data = {
            "threadId": 161001,
            "commentId": 1771800001,
            "status": "in-progress",
            "files": ["/mgmt-backend/SomeFile.cs"],
        }
        f = FolderGroup.from_dict(data)
        assert f.files == ["/mgmt-backend/SomeFile.cs"]
        assert not hasattr(f, "threadId") or not isinstance(getattr(f, "threadId", None), int)
