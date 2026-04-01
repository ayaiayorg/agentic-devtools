"""Tests for agentic_devtools.cli.git.diff.get_diff_lines_info."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.git.diff import get_diff_lines_info


class TestGetDiffLinesInfo:
    """Tests for get_diff_lines_info function."""

    def test_returns_empty_on_error(self):
        """Should return empty info on git command failure."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        with patch("agentic_devtools.cli.git.diff.run_safe", return_value=mock_result):
            result = get_diff_lines_info("main", "feature", "file.py")

            assert result.added.lines == []
            assert result.added.is_binary is False
            assert result.removed.lines == []
            assert result.removed.is_binary is False

    def test_returns_empty_on_no_changes(self):
        """Should return empty info when no changes."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("agentic_devtools.cli.git.diff.run_safe", return_value=mock_result):
            result = get_diff_lines_info("main", "feature", "file.py")

            assert result.added.lines == []
            assert result.removed.lines == []

    def test_detects_binary_file(self):
        """Should detect binary files in both added and removed info."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "diff --git a/image.png b/image.png\nBinary files a/image.png and b/image.png differ"

        with patch("agentic_devtools.cli.git.diff.run_safe", return_value=mock_result):
            result = get_diff_lines_info("main", "feature", "image.png")

            assert result.added.is_binary is True
            assert result.removed.is_binary is True
            assert result.added.lines == []
            assert result.removed.lines == []

    def test_parses_added_and_removed_lines(self):
        """Should parse both added and removed lines from a single diff."""
        diff_output = """diff --git a/file.py b/file.py
--- a/file.py
+++ b/file.py
@@ -1,4 +1,4 @@
 line 1
-old line 2
+new line 2
 line 3
 line 4"""

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = diff_output

        with patch("agentic_devtools.cli.git.diff.run_safe", return_value=mock_result):
            result = get_diff_lines_info("main", "feature", "file.py")

            assert len(result.added.lines) == 1
            assert result.added.lines[0].content == "new line 2"
            assert result.added.lines[0].line_number == 2

            assert len(result.removed.lines) == 1
            assert result.removed.lines[0].content == "old line 2"
            assert result.removed.lines[0].line_number == 2

    def test_parses_multiple_hunks(self):
        """Should parse multiple hunks correctly for both added and removed."""
        diff_output = """@@ -1,3 +1,3 @@
 line 1
-removed at line 2
+added at line 2
 line 3
@@ -10,3 +10,3 @@
 line 10
-removed at line 11
+added at line 11
 line 12"""

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = diff_output

        with patch("agentic_devtools.cli.git.diff.run_safe", return_value=mock_result):
            result = get_diff_lines_info("main", "feature", "file.py")

            assert len(result.added.lines) == 2
            assert result.added.lines[0].line_number == 2
            assert result.added.lines[1].line_number == 11

            assert len(result.removed.lines) == 2
            assert result.removed.lines[0].line_number == 2
            assert result.removed.lines[1].line_number == 11

    def test_only_added_lines(self):
        """Should handle diff with only additions."""
        diff_output = """@@ -1,2 +1,3 @@
 line 1
+new line 2
 line 2"""

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = diff_output

        with patch("agentic_devtools.cli.git.diff.run_safe", return_value=mock_result):
            result = get_diff_lines_info("main", "feature", "file.py")

            assert len(result.added.lines) == 1
            assert result.added.lines[0].content == "new line 2"
            assert len(result.removed.lines) == 0

    def test_only_removed_lines(self):
        """Should handle diff with only removals."""
        diff_output = """@@ -1,3 +1,2 @@
 line 1
-removed line
 line 3"""

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = diff_output

        with patch("agentic_devtools.cli.git.diff.run_safe", return_value=mock_result):
            result = get_diff_lines_info("main", "feature", "file.py")

            assert len(result.added.lines) == 0
            assert len(result.removed.lines) == 1
            assert result.removed.lines[0].content == "removed line"

    def test_uses_repo_root_relative_path(self):
        """Should use :/ prefix to make path repo-root-relative."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("agentic_devtools.cli.git.diff.run_safe", return_value=mock_result) as mock_run:
            get_diff_lines_info("main", "feature", "src/file.py")

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
            result = get_diff_lines_info("main", "feature", "file.py")

            assert len(result.removed.lines) == 1
            assert result.removed.lines[0].content == "--decrement operator"

    def test_does_not_skip_content_starting_with_double_plus(self):
        """Should not skip added lines whose content starts with '++'."""
        diff_output = """@@ -1,2 +1,3 @@
 line 1
+++increment operator
 line 2"""

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = diff_output

        with patch("agentic_devtools.cli.git.diff.run_safe", return_value=mock_result):
            result = get_diff_lines_info("main", "feature", "file.py")

            assert len(result.added.lines) == 1
            assert result.added.lines[0].content == "++increment operator"

    def test_does_not_skip_content_starting_with_double_plus_space(self):
        """Should not skip added lines whose content starts with '++ ' (two plus + space)."""
        diff_output = """@@ -1,2 +1,3 @@
 line 1
+++ spaced content
 line 2"""

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = diff_output

        with patch("agentic_devtools.cli.git.diff.run_safe", return_value=mock_result):
            result = get_diff_lines_info("main", "feature", "file.py")

            assert len(result.added.lines) == 1
            assert result.added.lines[0].content == "++ spaced content"

    def test_does_not_skip_content_starting_with_double_dash_space(self):
        """Should not skip removed lines whose content starts with '-- ' (two dashes + space)."""
        diff_output = """@@ -1,3 +1,2 @@
 line 1
--- spaced content
 line 3"""

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = diff_output

        with patch("agentic_devtools.cli.git.diff.run_safe", return_value=mock_result):
            result = get_diff_lines_info("main", "feature", "file.py")

            assert len(result.removed.lines) == 1
            assert result.removed.lines[0].content == "-- spaced content"

    def test_single_subprocess_call(self):
        """Should only invoke git diff once (not twice as before)."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = """@@ -1,2 +1,2 @@
 line 1
-old
+new"""

        with patch("agentic_devtools.cli.git.diff.run_safe", return_value=mock_result) as mock_run:
            get_diff_lines_info("main", "feature", "file.py")

            assert mock_run.call_count == 1
