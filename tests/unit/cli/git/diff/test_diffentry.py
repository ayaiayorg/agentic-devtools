"""Tests for agentic_devtools.cli.git.diff.DiffEntry."""

from agentic_devtools.cli.git.diff import DiffEntry


class TestDiffEntry:
    """Tests for DiffEntry dataclass."""

    def test_diff_entry_creation(self):
        """Should create DiffEntry with all fields."""
        entry = DiffEntry(path="src/main.py", status="M", change_type="M", original_path=None)
        assert entry.path == "src/main.py"
        assert entry.status == "M"
        assert entry.change_type == "M"
        assert entry.original_path is None

    def test_diff_entry_with_rename(self):
        """Should create DiffEntry for rename with original path."""
        entry = DiffEntry(
            path="src/new_name.py",
            status="R100",
            change_type="R",
            original_path="src/old_name.py",
        )
        assert entry.path == "src/new_name.py"
        assert entry.original_path == "src/old_name.py"
        assert entry.change_type == "R"
