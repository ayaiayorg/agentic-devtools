"""
Tests for mark_reviewed module - Azure DevOps PR file review marking.
"""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure_devops.mark_reviewed import (
    AuthenticatedUser,
    ChangeEntry,
    _extract_authenticated_user,
    _get_graph_api_root,
    _get_organization_account_name,
    normalize_repo_path,
)



class TestMarkFileReviewedDryRun:
    """Tests for mark_file_reviewed in dry-run mode."""

    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.require_requests")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.get_pat")
    def test_dry_run_skips_api_calls(self, mock_pat, mock_requests, capsys):
        """Test that dry run doesn't make API calls."""
        from agentic_devtools.cli.azure_devops.config import AzureDevOpsConfig
        from agentic_devtools.cli.azure_devops.mark_reviewed import mark_file_reviewed

        config = AzureDevOpsConfig(
            organization="https://dev.azure.com/test",
            project="TestProject",
            repository="TestRepo",
        )

        result = mark_file_reviewed(
            file_path="src/test.ts",
            pull_request_id=123,
            config=config,
            repo_id="repo-guid",
            dry_run=True,
        )

        assert result is True
        # require_requests and get_pat should NOT be called in dry-run
        mock_requests.assert_not_called()
        mock_pat.assert_not_called()

        captured = capsys.readouterr()
        assert "DRY-RUN" in captured.out

    def test_dry_run_invalid_path_returns_false(self, capsys):
        """Test that dry run with invalid path returns False."""
        from agentic_devtools.cli.azure_devops.config import AzureDevOpsConfig
        from agentic_devtools.cli.azure_devops.mark_reviewed import mark_file_reviewed

        config = AzureDevOpsConfig(
            organization="https://dev.azure.com/test",
            project="TestProject",
            repository="TestRepo",
        )

        result = mark_file_reviewed(
            file_path="",  # Empty path
            pull_request_id=123,
            config=config,
            repo_id="repo-guid",
            dry_run=True,
        )

        assert result is False
        captured = capsys.readouterr()
        assert "Invalid file path" in captured.err


class TestMarkFileReviewedMainPath:
    """Tests for the main mark_file_reviewed function execution path."""

    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.require_requests")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.get_pat")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.get_auth_headers")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed._get_connection_data")
    def test_fails_on_connection_data_error(self, mock_conn_data, mock_headers, mock_pat, mock_requests, capsys):
        """Test returns False when connection data retrieval fails."""
        from agentic_devtools.cli.azure_devops.config import AzureDevOpsConfig
        from agentic_devtools.cli.azure_devops.mark_reviewed import mark_file_reviewed

        mock_requests.return_value = MagicMock()
        mock_pat.return_value = "pat123"
        mock_headers.return_value = {"Authorization": "Basic xxx"}
        mock_conn_data.side_effect = Exception("Connection failed")

        config = AzureDevOpsConfig(
            organization="https://dev.azure.com/test",
            project="TestProject",
            repository="TestRepo",
        )

        result = mark_file_reviewed(
            file_path="src/test.ts",
            pull_request_id=123,
            config=config,
            repo_id="repo-guid",
            dry_run=False,
        )

        assert result is False
        captured = capsys.readouterr()
        assert "Failed to retrieve Azure DevOps connection data" in captured.err

    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.require_requests")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.get_pat")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.get_auth_headers")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed._get_connection_data")
    def test_fails_when_cannot_resolve_reviewer_id(self, mock_conn_data, mock_headers, mock_pat, mock_requests, capsys):
        """Test returns False when reviewer ID cannot be resolved."""
        from agentic_devtools.cli.azure_devops.config import AzureDevOpsConfig
        from agentic_devtools.cli.azure_devops.mark_reviewed import mark_file_reviewed

        mock_requests.return_value = MagicMock()
        mock_pat.return_value = "pat123"
        mock_headers.return_value = {"Authorization": "Basic xxx"}
        mock_conn_data.return_value = {
            "authenticatedUser": {
                # No storageKey, no descriptor, no subjectDescriptor
            }
        }

        config = AzureDevOpsConfig(
            organization="https://dev.azure.com/test",
            project="TestProject",
            repository="TestRepo",
        )

        result = mark_file_reviewed(
            file_path="src/test.ts",
            pull_request_id=123,
            config=config,
            repo_id="repo-guid",
            dry_run=False,
        )

        assert result is False
        captured = capsys.readouterr()
        assert "Unable to resolve reviewer identity" in captured.err

    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.require_requests")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.get_pat")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.get_auth_headers")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed._get_connection_data")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed._get_reviewer_entry")
    def test_fails_on_reviewer_entry_error(
        self, mock_reviewer_entry, mock_conn_data, mock_headers, mock_pat, mock_requests, capsys
    ):
        """Test returns False when getting reviewer entry fails."""
        from agentic_devtools.cli.azure_devops.config import AzureDevOpsConfig
        from agentic_devtools.cli.azure_devops.mark_reviewed import mark_file_reviewed

        mock_requests.return_value = MagicMock()
        mock_pat.return_value = "pat123"
        mock_headers.return_value = {"Authorization": "Basic xxx"}
        mock_conn_data.return_value = {"authenticatedUser": {"storageKey": "guid-123"}}
        mock_reviewer_entry.side_effect = Exception("API error")

        config = AzureDevOpsConfig(
            organization="https://dev.azure.com/test",
            project="TestProject",
            repository="TestRepo",
        )

        result = mark_file_reviewed(
            file_path="src/test.ts",
            pull_request_id=123,
            config=config,
            repo_id="repo-guid",
            dry_run=False,
        )

        assert result is False
        captured = capsys.readouterr()
        assert "Failed to retrieve reviewer entry" in captured.err

    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.require_requests")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.get_pat")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.get_auth_headers")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed._get_connection_data")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed._get_reviewer_entry")
    def test_returns_true_when_already_reviewed(
        self, mock_reviewer_entry, mock_conn_data, mock_headers, mock_pat, mock_requests, capsys
    ):
        """Test returns True when file is already marked as reviewed."""
        from agentic_devtools.cli.azure_devops.config import AzureDevOpsConfig
        from agentic_devtools.cli.azure_devops.mark_reviewed import mark_file_reviewed

        mock_requests.return_value = MagicMock()
        mock_pat.return_value = "pat123"
        mock_headers.return_value = {"Authorization": "Basic xxx"}
        mock_conn_data.return_value = {
            "authenticatedUser": {"storageKey": "guid-123", "providerDisplayName": "Test User"}
        }
        mock_reviewer_entry.return_value = {
            "reviewedFiles": ["/src/test.ts"],
        }

        config = AzureDevOpsConfig(
            organization="https://dev.azure.com/test",
            project="TestProject",
            repository="TestRepo",
        )

        result = mark_file_reviewed(
            file_path="src/test.ts",
            pull_request_id=123,
            config=config,
            repo_id="repo-guid",
            dry_run=False,
        )

        assert result is True
        captured = capsys.readouterr()
        assert "already marked as reviewed" in captured.out

    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.require_requests")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.get_pat")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.get_auth_headers")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed._get_connection_data")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed._get_reviewer_entry")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed._update_reviewer_entry")
    def test_fails_on_update_reviewer_entry_error(
        self, mock_update, mock_reviewer_entry, mock_conn_data, mock_headers, mock_pat, mock_requests, capsys
    ):
        """Test returns False when updating reviewer entry fails."""
        from agentic_devtools.cli.azure_devops.config import AzureDevOpsConfig
        from agentic_devtools.cli.azure_devops.mark_reviewed import mark_file_reviewed

        mock_requests.return_value = MagicMock()
        mock_pat.return_value = "pat123"
        mock_headers.return_value = {"Authorization": "Basic xxx"}
        mock_conn_data.return_value = {"authenticatedUser": {"storageKey": "guid-123"}}
        mock_reviewer_entry.return_value = {"reviewedFiles": []}
        mock_update.side_effect = Exception("Update failed")

        config = AzureDevOpsConfig(
            organization="https://dev.azure.com/test",
            project="TestProject",
            repository="TestRepo",
        )

        result = mark_file_reviewed(
            file_path="src/test.ts",
            pull_request_id=123,
            config=config,
            repo_id="repo-guid",
            dry_run=False,
        )

        assert result is False
        captured = capsys.readouterr()
        assert "Failed to update reviewer entry" in captured.err
