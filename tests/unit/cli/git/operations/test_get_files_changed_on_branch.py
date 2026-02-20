"""Tests for agentic_devtools.cli.git.operations.get_files_changed_on_branch."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.git import operations


class TestGetFilesChangedOnBranch:
    """Tests for get_files_changed_on_branch function."""

    def test_returns_files_when_branch_has_changes(self, mock_run_safe):
        """Test returns list of files when branch has changes."""
        with patch.object(operations, "run_git") as mock_run_git:
            mock_run_git.return_value = MagicMock(
                returncode=0,
                stdout="src/file1.ts\nsrc/file2.ts\nREADME.md\n",
                stderr="",
            )

            result = operations.get_files_changed_on_branch()

            assert isinstance(result, list)
            assert len(result) == 3
            assert "src/file1.ts" in result
            assert "src/file2.ts" in result
            assert "README.md" in result

    def test_returns_empty_list_when_no_changes(self, mock_run_safe):
        """Test returns empty list when branch has no changes."""
        with patch.object(operations, "run_git") as mock_run_git:
            mock_run_git.return_value = MagicMock(returncode=0, stdout="", stderr="")

            result = operations.get_files_changed_on_branch()

            assert isinstance(result, list)
            assert len(result) == 0

    def test_falls_back_to_main_if_origin_main_not_found(self, mock_run_safe):
        """Test falls back to 'main' if 'origin/main' doesn't exist."""
        with patch.object(operations, "run_git") as mock_run_git:
            mock_run_git.side_effect = [
                MagicMock(returncode=1, stdout="", stderr="error"),
                MagicMock(returncode=0, stdout="file.ts\n", stderr=""),
            ]

            result = operations.get_files_changed_on_branch()

            assert isinstance(result, list)
            assert "file.ts" in result

    def test_returns_empty_list_on_error(self, mock_run_safe):
        """Test returns empty list on git command error."""
        with patch.object(operations, "run_git") as mock_run_git:
            mock_run_git.side_effect = [
                MagicMock(returncode=1, stdout="", stderr="error"),
                MagicMock(returncode=1, stdout="", stderr="error"),
            ]

            result = operations.get_files_changed_on_branch()

            assert isinstance(result, list)
            assert len(result) == 0

    def test_uses_custom_main_branch(self, mock_run_safe):
        """Test uses custom main branch name."""
        with patch.object(operations, "run_git") as mock_run_git:
            mock_run_git.return_value = MagicMock(returncode=0, stdout="file.ts\n", stderr="")

            result = operations.get_files_changed_on_branch(main_branch="develop")

            assert "file.ts" in result
            first_call = mock_run_git.call_args_list[0][0]
            assert "origin/develop...HEAD" in first_call
