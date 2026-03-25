"""Tests for get_repository_id helper."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli import azure_devops


class TestGetRepositoryId:
    """Tests for get_repository_id function."""

    def test_uses_rest_as_first_lookup_option(self, mock_azure_devops_env):
        """Test repository ID is resolved from REST before Azure CLI is attempted."""
        with patch(
            "agentic_devtools.cli.azure_devops.helpers._get_repository_id_via_rest", return_value="repo-guid-123"
        ):
            with patch("agentic_devtools.cli.azure_devops.helpers.run_safe") as mock_run_safe:
                repo_id = azure_devops.get_repository_id()

        assert repo_id == "repo-guid-123"
        mock_run_safe.assert_not_called()

    def test_falls_back_to_az_when_rest_lookup_fails(self):
        """Test Azure CLI is used when REST lookup fails."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "repo-guid-123\n"

        with patch(
            "agentic_devtools.cli.azure_devops.helpers._get_repository_id_via_rest",
            side_effect=RuntimeError("REST failed"),
        ):
            with patch("agentic_devtools.cli.azure_devops.helpers.run_safe", return_value=mock_result):
                repo_id = azure_devops.get_repository_id()

        assert repo_id == "repo-guid-123"

    def test_raises_when_rest_and_az_fail(self):
        """Test error contains both REST and Azure CLI failures."""
        cli_result = MagicMock()
        cli_result.returncode = 1
        cli_result.stderr = "VS800075"

        with patch(
            "agentic_devtools.cli.azure_devops.helpers._get_repository_id_via_rest",
            side_effect=RuntimeError("Forbidden"),
        ):
            with patch("agentic_devtools.cli.azure_devops.helpers.run_safe", return_value=cli_result):
                with pytest.raises(RuntimeError, match="REST lookup failed") as exc_info:
                    azure_devops.get_repository_id(
                        organization="https://dev.azure.com/swica",
                        project="DragonflyMgmt",
                        repository="dfly-platform-management",
                    )

        assert "Azure CLI fallback failed" in str(exc_info.value)

    def test_raises_when_rest_fails_and_az_returns_empty_result(self):
        """Test empty Azure CLI fallback result is surfaced after REST failure."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch(
            "agentic_devtools.cli.azure_devops.helpers._get_repository_id_via_rest",
            side_effect=RuntimeError("Forbidden"),
        ):
            with patch("agentic_devtools.cli.azure_devops.helpers.run_safe", return_value=mock_result):
                with pytest.raises(RuntimeError, match="Empty repository ID"):
                    azure_devops.get_repository_id()
