"""Tests for agentic_devtools.cli.git.diff.get_removed_lines_info."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.git.diff import get_removed_lines_info


class TestGetRemovedLinesInfo:
    """Tests for get_removed_lines_info function."""

    def test_returns_empty_on_error(self):
        """Should return empty info on git command failure."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        with patch("agentic_devtools.cli.git.diff.run_safe", return_value=mock_result):
            result = get_removed_lines_info("main", "feature", "file.py")

            assert result.lines == []
            assert result.is_binary is False

    def test_returns_empty_on_no_changes(self):
        """Should return empty info when no changes."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("agentic_devtools.cli.git.diff.run_safe", return_value=mock_result):
            result = get_removed_lines_info("main", "feature", "file.py")

            assert result.lines == []
            assert result.is_binary is False

    def test_detects_binary_file(self):
        """Should detect binary files with realistic diff --git header."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "diff --git a/image.png b/image.png\nBinary files a/image.png and b/image.png differ"

        with patch("agentic_devtools.cli.git.diff.run_safe", return_value=mock_result):
            result = get_removed_lines_info("main", "feature", "image.png")

            assert result.lines == []
            assert result.is_binary is True

    def test_parses_removed_lines(self):
        """Should parse removed lines from diff output with correct old-file line numbers."""
        diff_output = """diff --git a/file.py b/file.py
--- a/file.py
+++ b/file.py
@@ -1,4 +1,3 @@
 line 1
-old line 2
 line 3
 line 4"""

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = diff_output

        with patch("agentic_devtools.cli.git.diff.run_safe", return_value=mock_result):
            result = get_removed_lines_info("main", "feature", "file.py")

            assert len(result.lines) == 1
            assert result.lines[0].line_number == 2
            assert result.lines[0].content == "old line 2"
            assert result.is_binary is False

    def test_parses_multiple_hunks(self):
        """Should parse multiple hunks correctly with old-file line numbers."""
        diff_output = """@@ -1,3 +1,2 @@
 line 1
-removed at line 2
 line 3
@@ -10,3 +9,2 @@
 line 10
-removed at line 11
 line 12"""

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = diff_output

        with patch("agentic_devtools.cli.git.diff.run_safe", return_value=mock_result):
            result = get_removed_lines_info("main", "feature", "file.py")

            assert len(result.lines) == 2
            assert result.lines[0].line_number == 2
            assert result.lines[0].content == "removed at line 2"
            assert result.lines[1].line_number == 11
            assert result.lines[1].content == "removed at line 11"

    def test_ignores_added_lines(self):
        """Should not count added lines."""
        diff_output = """@@ -1,2 +1,3 @@
 line 1
+added line
 line 2"""

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = diff_output

        with patch("agentic_devtools.cli.git.diff.run_safe", return_value=mock_result):
            result = get_removed_lines_info("main", "feature", "file.py")

            assert len(result.lines) == 0

    def test_uses_repo_root_relative_path(self):
        """Should use :/ prefix to make path repo-root-relative."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("agentic_devtools.cli.git.diff.run_safe", return_value=mock_result) as mock_run:
            get_removed_lines_info("main", "feature", "src/file.py")

            call_args = mock_run.call_args[0][0]
            assert ":/src/file.py" in call_args

    def test_does_not_skip_content_starting_with_double_dash(self):
        """Should not skip removed lines whose content starts with '--'."""
        diff_output = """@@ -1,3 +1,2 @@
 line 1
---decrement operator
 line 3"""

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = diff_output

        with patch("agentic_devtools.cli.git.diff.run_safe", return_value=mock_result):
            result = get_removed_lines_info("main", "feature", "file.py")

            assert len(result.lines) == 1
            assert result.lines[0].content == "--decrement operator"
