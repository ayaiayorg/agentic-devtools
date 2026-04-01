"""Tests for agentic_devtools.cli.git.diff._is_diff_file_header."""

from agentic_devtools.cli.git.diff import _is_diff_file_header


class TestIsDiffFileHeader:
    """Tests for _is_diff_file_header helper."""

    def test_old_file_header(self):
        """Should match old-file header '--- a/path'."""
        assert _is_diff_file_header("--- a/file.py") is True

    def test_new_file_header(self):
        """Should match new-file header '+++ b/path'."""
        assert _is_diff_file_header("+++ b/file.py") is True

    def test_old_dev_null(self):
        """Should match '--- /dev/null' for new files."""
        assert _is_diff_file_header("--- /dev/null") is True

    def test_new_dev_null(self):
        """Should match '+++ /dev/null' for deleted files."""
        assert _is_diff_file_header("+++ /dev/null") is True

    def test_removed_content_with_double_dash(self):
        """Should NOT match removed content starting with '--' (no space)."""
        assert _is_diff_file_header("---decrement") is False

    def test_added_content_with_double_plus(self):
        """Should NOT match added content starting with '++' (no space)."""
        assert _is_diff_file_header("+++increment") is False

    def test_removed_content_with_double_dash_space(self):
        """Should NOT match removed content starting with '-- ' (two dashes + space)."""
        assert _is_diff_file_header("--- spaced content") is False

    def test_added_content_with_double_plus_space(self):
        """Should NOT match added content starting with '++ ' (two plus + space)."""
        assert _is_diff_file_header("+++ spaced content") is False

    def test_regular_added_line(self):
        """Should NOT match a regular added line."""
        assert _is_diff_file_header("+regular line") is False

    def test_regular_removed_line(self):
        """Should NOT match a regular removed line."""
        assert _is_diff_file_header("-regular line") is False

    def test_context_line(self):
        """Should NOT match a context line."""
        assert _is_diff_file_header(" context line") is False

    def test_empty_line(self):
        """Should NOT match an empty line."""
        assert _is_diff_file_header("") is False

    def test_hunk_header(self):
        """Should NOT match a hunk header."""
        assert _is_diff_file_header("@@ -1,3 +1,4 @@") is False
