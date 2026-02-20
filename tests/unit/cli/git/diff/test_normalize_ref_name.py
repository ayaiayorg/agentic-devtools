"""Tests for agentic_devtools.cli.git.diff.normalize_ref_name."""

from agentic_devtools.cli.git.diff import (
    AddedLine,
    AddedLinesInfo,
    DiffEntry,
    normalize_ref_name,
)


class TestNormalizeRefName:
    """Tests for normalize_ref_name function."""

    def test_strips_refs_heads_prefix(self):
        """Should strip refs/heads/ prefix from ref names."""
        result = normalize_ref_name("refs/heads/main")
        assert result == "main"

    def test_strips_refs_heads_prefix_with_slashes(self):
        """Should handle ref names with slashes."""
        result = normalize_ref_name("refs/heads/feature/my-branch")
        assert result == "feature/my-branch"

    def test_returns_unchanged_if_no_prefix(self):
        """Should return ref unchanged if no prefix."""
        result = normalize_ref_name("main")
        assert result == "main"

    def test_returns_none_for_none(self):
        """Should return None for None input."""
        result = normalize_ref_name(None)
        assert result is None

    def test_returns_none_for_empty_string(self):
        """Should return None for empty string."""
        result = normalize_ref_name("")
        assert result is None


class TestDataClasses:
    """Tests for diff module data classes."""

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

    def test_added_line_creation(self):
        """Should create AddedLine with line number and content."""
        line = AddedLine(line_number=42, content="def hello():")
        assert line.line_number == 42
        assert line.content == "def hello():"

    def test_added_lines_info_creation(self):
        """Should create AddedLinesInfo with lines and binary flag."""
        lines = [AddedLine(1, "line 1"), AddedLine(2, "line 2")]
        info = AddedLinesInfo(lines=lines, is_binary=False)
        assert len(info.lines) == 2
        assert info.is_binary is False

    def test_added_lines_info_binary(self):
        """Should create AddedLinesInfo for binary file."""
        info = AddedLinesInfo(lines=[], is_binary=True)
        assert len(info.lines) == 0
        assert info.is_binary is True
