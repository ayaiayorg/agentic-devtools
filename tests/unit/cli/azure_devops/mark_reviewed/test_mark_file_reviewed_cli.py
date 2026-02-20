"""Tests for mark_file_reviewed_cli function."""
from unittest.mock import MagicMock, patch

class TestMarkFileReviewedCli:
    """Tests for mark_file_reviewed_cli entry point."""

    def test_cli_requires_file_path(self, temp_state_dir, clear_state_before, capsys):
        """Test CLI exits with error when file_path not set."""
        import pytest

        from agentic_devtools.cli.azure_devops.mark_reviewed import mark_file_reviewed_cli
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "123")
        set_value("azure_devops.organization", "https://dev.azure.com/test")
        set_value("azure_devops.project", "proj")
        set_value("azure_devops.repository", "repo")
        # Not setting file_review.file_path

        with pytest.raises(SystemExit) as exc_info:
            mark_file_reviewed_cli()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "file_review.file_path" in captured.err

    def test_cli_requires_pull_request_id(self, temp_state_dir, clear_state_before):
        """Test CLI exits with error when pull_request_id not set."""
        import pytest

        from agentic_devtools.cli.azure_devops.mark_reviewed import mark_file_reviewed_cli
        from agentic_devtools.state import set_value

        set_value("file_review.file_path", "/src/test.ts")
        set_value("azure_devops.organization", "https://dev.azure.com/test")
        set_value("azure_devops.project", "proj")
        set_value("azure_devops.repository", "repo")
        # Not setting pull_request_id

        with pytest.raises(KeyError, match="pull_request_id"):
            mark_file_reviewed_cli()

    @patch("agentic_devtools.cli.azure_devops.helpers.get_repository_id")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.mark_file_reviewed")
    def test_cli_success_path(self, mock_mark, mock_repo_id, temp_state_dir, clear_state_before):
        """Test CLI calls mark_file_reviewed with correct parameters."""
        from agentic_devtools.cli.azure_devops.mark_reviewed import mark_file_reviewed_cli
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "123")
        set_value("file_review.file_path", "/src/test.ts")
        set_value("azure_devops.organization", "https://dev.azure.com/test")
        set_value("azure_devops.project", "proj")
        set_value("azure_devops.repository", "repo")

        mock_repo_id.return_value = "repo-guid"
        mock_mark.return_value = True

        mark_file_reviewed_cli()

        mock_mark.assert_called_once()
        call_args = mock_mark.call_args
        assert call_args.kwargs["file_path"] == "/src/test.ts"
        assert call_args.kwargs["pull_request_id"] == 123

    @patch("agentic_devtools.cli.azure_devops.helpers.get_repository_id")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.mark_file_reviewed")
    def test_cli_exits_on_failure(self, mock_mark, mock_repo_id, temp_state_dir, clear_state_before):
        """Test CLI exits with code 1 when mark_file_reviewed returns False."""
        import pytest

        from agentic_devtools.cli.azure_devops.mark_reviewed import mark_file_reviewed_cli
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "123")
        set_value("file_review.file_path", "/src/test.ts")
        set_value("azure_devops.organization", "https://dev.azure.com/test")
        set_value("azure_devops.project", "proj")
        set_value("azure_devops.repository", "repo")

        mock_repo_id.return_value = "repo-guid"
        mock_mark.return_value = False

        with pytest.raises(SystemExit) as exc_info:
            mark_file_reviewed_cli()

        assert exc_info.value.code == 1
