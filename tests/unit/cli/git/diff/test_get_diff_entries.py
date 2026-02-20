"""Tests for agentic_devtools.cli.git.diff.get_diff_entries."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.git.diff import get_diff_entries


class TestGetDiffEntries:
    """Tests for get_diff_entries function."""

    def test_returns_empty_list_on_error(self):
        """Should return empty list when git command fails."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        with patch("agentic_devtools.cli.git.diff.run_safe", return_value=mock_result):
            result = get_diff_entries("main", "feature")
            assert result == []

    def test_returns_empty_list_on_empty_output(self):
        """Should return empty list when no changes."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("agentic_devtools.cli.git.diff.run_safe", return_value=mock_result):
            result = get_diff_entries("main", "feature")
            assert result == []

    def test_parses_modified_file(self):
        """Should parse modified file status."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "M\tsrc/main.py"

        with patch("agentic_devtools.cli.git.diff.run_safe", return_value=mock_result):
            result = get_diff_entries("main", "feature")

            assert len(result) == 1
            assert result[0].path == "src/main.py"
            assert result[0].status == "M"
            assert result[0].change_type == "M"

    def test_parses_added_file(self):
        """Should parse added file status."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "A\tnew_file.py"

        with patch("agentic_devtools.cli.git.diff.run_safe", return_value=mock_result):
            result = get_diff_entries("main", "feature")

            assert len(result) == 1
            assert result[0].path == "new_file.py"
            assert result[0].change_type == "A"

    def test_parses_deleted_file(self):
        """Should parse deleted file status."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "D\told_file.py"

        with patch("agentic_devtools.cli.git.diff.run_safe", return_value=mock_result):
            result = get_diff_entries("main", "feature")

            assert len(result) == 1
            assert result[0].path == "old_file.py"
            assert result[0].change_type == "D"

    def test_parses_renamed_file(self):
        """Should parse renamed file with original path."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "R100\told_name.py\tnew_name.py"

        with patch("agentic_devtools.cli.git.diff.run_safe", return_value=mock_result):
            result = get_diff_entries("main", "feature")

            assert len(result) == 1
            assert result[0].path == "new_name.py"
            assert result[0].original_path == "old_name.py"
            assert result[0].change_type == "R"

    def test_parses_multiple_files(self):
        """Should parse multiple file changes."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "M\tfile1.py\nA\tfile2.py\nD\tfile3.py"

        with patch("agentic_devtools.cli.git.diff.run_safe", return_value=mock_result):
            result = get_diff_entries("main", "feature")

            assert len(result) == 3
            assert result[0].path == "file1.py"
            assert result[1].path == "file2.py"
            assert result[2].path == "file3.py"

    def test_skips_empty_lines(self):
        """Should skip empty lines in output."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "M\tfile1.py\n\nA\tfile2.py"

        with patch("agentic_devtools.cli.git.diff.run_safe", return_value=mock_result):
            result = get_diff_entries("main", "feature")

            assert len(result) == 2

    def test_skips_malformed_lines(self):
        """Should skip lines without tab separator."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "M\tfile1.py\nmalformed line\nA\tfile2.py"

        with patch("agentic_devtools.cli.git.diff.run_safe", return_value=mock_result):
            result = get_diff_entries("main", "feature")

            assert len(result) == 2
