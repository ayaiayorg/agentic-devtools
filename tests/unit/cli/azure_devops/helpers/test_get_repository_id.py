"""Tests for get_repository_id helper."""
from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli import azure_devops


class TestGetRepositoryId:
    """Tests for get_repository_id function."""

    def test_successful_repo_id_fetch(self):
        """Test successful repository ID fetch."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "repo-guid-123\n"

        with patch("subprocess.run", return_value=mock_result):
            repo_id = azure_devops.get_repository_id()
            assert repo_id == "repo-guid-123"

    def test_raises_on_command_failure(self):
        """Test raises RuntimeError on command failure."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Command failed"

        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(RuntimeError, match="Failed to get repository ID"):
                azure_devops.get_repository_id()

    def test_raises_on_empty_result(self):
        """Test raises RuntimeError on empty result."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(RuntimeError, match="Empty repository ID"):
                azure_devops.get_repository_id()
