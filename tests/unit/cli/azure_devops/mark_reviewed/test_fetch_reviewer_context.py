"""Tests for fetch_reviewer_context function."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.azure_devops.config import AzureDevOpsConfig
from agentic_devtools.cli.azure_devops.mark_reviewed import (
    CachedReviewerContext,
    fetch_reviewer_context,
)


class TestFetchReviewerContext:
    """Tests for the fetch_reviewer_context one-time setup function."""

    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.require_requests")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.get_pat")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.get_auth_headers")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed._get_connection_data")
    def test_returns_valid_context(self, mock_conn, mock_auth, mock_pat, mock_req, capsys):
        """Test that fetch_reviewer_context returns a populated CachedReviewerContext."""
        mock_requests = MagicMock()
        mock_req.return_value = mock_requests
        mock_pat.return_value = "pat123"
        mock_auth.return_value = {"Authorization": "Basic xxx"}
        mock_conn.return_value = {
            "authenticatedUser": {
                "storageKey": "guid-456",
                "providerDisplayName": "Test User",
                "descriptor": "aad.123",
            },
            "instanceId": "inst-1",
        }

        config = AzureDevOpsConfig(
            organization="https://dev.azure.com/test-org",
            project="TestProject",
            repository="TestRepo",
        )

        ctx = fetch_reviewer_context(config)

        assert isinstance(ctx, CachedReviewerContext)
        assert ctx.requests is mock_requests
        assert ctx.headers == {"Authorization": "Basic xxx"}
        assert ctx.auth_user.display_name == "Test User"
        assert ctx.auth_user.storage_key == "guid-456"
        assert ctx.reviewer_id == "guid-456"
        assert ctx.instance_id == "inst-1"
        assert ctx.organization_account_name == "test-org"
        assert ctx.reviewer_entry is None  # Lazily populated

        captured = capsys.readouterr()
        assert "cached for batch" in captured.out
        assert "Authenticated as" in captured.out

    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.require_requests")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.get_pat")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.get_auth_headers")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed._get_connection_data")
    def test_raises_when_no_reviewer_id(self, mock_conn, mock_auth, mock_pat, mock_req):
        """Test that fetch_reviewer_context raises RuntimeError when reviewer_id cannot be resolved."""
        mock_req.return_value = MagicMock()
        mock_pat.return_value = "pat123"
        mock_auth.return_value = {"Authorization": "Basic xxx"}
        mock_conn.return_value = {
            "authenticatedUser": {
                # No storageKey, no descriptor, no subjectDescriptor
            }
        }

        config = AzureDevOpsConfig(
            organization="https://dev.azure.com/test-org",
            project="TestProject",
            repository="TestRepo",
        )

        with pytest.raises(RuntimeError, match="Unable to resolve reviewer identity"):
            fetch_reviewer_context(config)

    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.require_requests")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.get_pat")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed.get_auth_headers")
    @patch("agentic_devtools.cli.azure_devops.mark_reviewed._get_connection_data")
    def test_propagates_connection_error(self, mock_conn, mock_auth, mock_pat, mock_req):
        """Test that connection errors propagate to caller."""
        mock_req.return_value = MagicMock()
        mock_pat.return_value = "pat123"
        mock_auth.return_value = {"Authorization": "Basic xxx"}
        mock_conn.side_effect = Exception("Network error")

        config = AzureDevOpsConfig(
            organization="https://dev.azure.com/test-org",
            project="TestProject",
            repository="TestRepo",
        )

        with pytest.raises(Exception, match="Network error"):
            fetch_reviewer_context(config)
