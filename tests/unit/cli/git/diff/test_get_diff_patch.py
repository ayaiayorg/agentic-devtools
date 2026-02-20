"""Tests for agentic_devtools.cli.git.diff.get_diff_patch."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.git.diff import get_diff_patch


class TestGetDiffPatch:
    """Tests for get_diff_patch function."""

    def test_returns_none_on_error(self):
        """Should return None on git command failure."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        with patch("agentic_devtools.cli.git.diff.run_safe", return_value=mock_result):
            result = get_diff_patch("main", "feature", "file.py")
            assert result is None

    def test_returns_none_on_empty_output(self):
        """Should return None when no changes."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("agentic_devtools.cli.git.diff.run_safe", return_value=mock_result):
            result = get_diff_patch("main", "feature", "file.py")
            assert result is None

    def test_returns_stripped_patch(self):
        """Should return stripped diff patch."""
        patch_content = """diff --git a/file.py b/file.py
--- a/file.py
+++ b/file.py
@@ -1,2 +1,3 @@
 line 1
+new line
 line 2
"""

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = patch_content

        with patch("agentic_devtools.cli.git.diff.run_safe", return_value=mock_result):
            result = get_diff_patch("main", "feature", "file.py")

            assert result is not None
            assert "diff --git" in result
            assert "+new line" in result

    def test_uses_repo_root_relative_path(self):
        """Should use :/ prefix to make path repo-root-relative."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("agentic_devtools.cli.git.diff.run_safe", return_value=mock_result) as mock_run:
            get_diff_patch("main", "feature", "src/file.py")

            call_args = mock_run.call_args[0][0]
            assert ":/src/file.py" in call_args
