"""Tests for agentic_devtools.cli.git.diff.get_added_lines_info."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.git.diff import get_added_lines_info


class TestGetAddedLinesInfo:
    """Tests for get_added_lines_info function."""

    def test_returns_empty_on_error(self):
        """Should return empty info on git command failure."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        with patch("agentic_devtools.cli.git.diff.run_safe", return_value=mock_result):
            result = get_added_lines_info("main", "feature", "file.py")

            assert result.lines == []
            assert result.is_binary is False

    def test_returns_empty_on_no_changes(self):
        """Should return empty info when no changes."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("agentic_devtools.cli.git.diff.run_safe", return_value=mock_result):
            result = get_added_lines_info("main", "feature", "file.py")

            assert result.lines == []
            assert result.is_binary is False

    def test_detects_binary_file(self):
        """Should detect binary files."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Binary files a/image.png and b/image.png differ"

        with patch("agentic_devtools.cli.git.diff.run_safe", return_value=mock_result):
            result = get_added_lines_info("main", "feature", "image.png")

            assert result.lines == []
            assert result.is_binary is True

    def test_parses_added_lines(self):
        """Should parse added lines from diff output."""
        diff_output = """diff --git a/file.py b/file.py
--- a/file.py
+++ b/file.py
@@ -1,3 +1,4 @@
 line 1
+new line 2
 line 3
 line 4"""

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = diff_output

        with patch("agentic_devtools.cli.git.diff.run_safe", return_value=mock_result):
            result = get_added_lines_info("main", "feature", "file.py")

            assert len(result.lines) == 1
            assert result.lines[0].content == "new line 2"
            assert result.is_binary is False

    def test_parses_multiple_hunks(self):
        """Should parse multiple hunks correctly."""
        diff_output = """@@ -1,2 +1,3 @@
 line 1
+new at line 2
 line 2
@@ -10,2 +11,3 @@
 line 10
+new at line 12
 line 11"""

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = diff_output

        with patch("agentic_devtools.cli.git.diff.run_safe", return_value=mock_result):
            result = get_added_lines_info("main", "feature", "file.py")

            assert len(result.lines) == 2
            assert result.lines[0].content == "new at line 2"
            assert result.lines[1].content == "new at line 12"

    def test_ignores_removed_lines(self):
        """Should not count removed lines."""
        diff_output = """@@ -1,3 +1,2 @@
 line 1
-removed line
 line 3"""

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = diff_output

        with patch("agentic_devtools.cli.git.diff.run_safe", return_value=mock_result):
            result = get_added_lines_info("main", "feature", "file.py")

            assert len(result.lines) == 0

    def test_uses_repo_root_relative_path(self):
        """Should use :/ prefix to make path repo-root-relative."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("agentic_devtools.cli.git.diff.run_safe", return_value=mock_result) as mock_run:
            get_added_lines_info("main", "feature", "src/file.py")

            call_args = mock_run.call_args[0][0]
            assert ":/src/file.py" in call_args
