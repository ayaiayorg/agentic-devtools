"""Tests for FolderEntry dataclass."""

from agentic_devtools.cli.azure_devops.review_state import FolderEntry, ReviewStatus


class TestFolderEntry:
    """Tests for FolderEntry dataclass."""

    def test_creation_with_defaults(self):
        """Test creation with default status and files."""
        f = FolderEntry(threadId=161001, commentId=1771800001)
        assert f.threadId == 161001
        assert f.commentId == 1771800001
        assert f.status == ReviewStatus.UNREVIEWED
        assert f.files == []

    def test_creation_with_files(self):
        """Test creation with explicit files list."""
        files = ["/mgmt-backend/SomeFile.cs", "/mgmt-backend/OtherFile.cs"]
        f = FolderEntry(threadId=1, commentId=2, files=files)
        assert f.files == files

    def test_to_dict(self):
        """Test serialization to dictionary."""
        files = ["/mgmt-backend/SomeFile.cs"]
        f = FolderEntry(threadId=161001, commentId=1771800001, status="in-progress", files=files)
        d = f.to_dict()
        assert d == {
            "threadId": 161001,
            "commentId": 1771800001,
            "status": "in-progress",
            "files": ["/mgmt-backend/SomeFile.cs"],
        }

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "threadId": 161001,
            "commentId": 1771800001,
            "status": "approved",
            "files": ["/mgmt-backend/SomeFile.cs"],
        }
        f = FolderEntry.from_dict(data)
        assert f.threadId == 161001
        assert f.commentId == 1771800001
        assert f.status == "approved"
        assert f.files == ["/mgmt-backend/SomeFile.cs"]

    def test_from_dict_defaults(self):
        """Test from_dict with missing optional fields uses defaults."""
        data = {"threadId": 1, "commentId": 2}
        f = FolderEntry.from_dict(data)
        assert f.status == ReviewStatus.UNREVIEWED
        assert f.files == []

    def test_roundtrip(self):
        """Test to_dict/from_dict round-trips correctly."""
        original = FolderEntry(
            threadId=5,
            commentId=10,
            status="needs-work",
            files=["/a/b.py", "/a/c.py"],
        )
        restored = FolderEntry.from_dict(original.to_dict())
        assert restored.threadId == 5
        assert restored.files == ["/a/b.py", "/a/c.py"]
        assert restored.status == "needs-work"

    def test_files_default_is_independent(self):
        """Test that default files lists are independent per instance."""
        f1 = FolderEntry(threadId=1, commentId=1)
        f2 = FolderEntry(threadId=2, commentId=2)
        f1.files.append("/some/file.cs")
        assert f2.files == []

    def test_from_dict_normalizes_file_paths(self):
        """Test that from_dict normalizes file paths with leading slash."""
        data = {
            "threadId": 1,
            "commentId": 2,
            "files": ["mgmt-backend/SomeFile.cs", "/mgmt-backend/OtherFile.cs"],
        }
        f = FolderEntry.from_dict(data)
        assert f.files == ["/mgmt-backend/SomeFile.cs", "/mgmt-backend/OtherFile.cs"]
