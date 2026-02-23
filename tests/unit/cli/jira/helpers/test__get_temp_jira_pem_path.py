"""
Tests for Jira helper utilities.
"""

from pathlib import Path
from unittest.mock import patch

from agdt_ai_helpers.cli.jira import helpers as jira_helpers


class TestGetJiraPemPaths:
    """Tests for _get_repo_jira_pem_path and _get_temp_jira_pem_path helpers."""

    def test_temp_path_returns_path_in_state_dir(self):
        """Test that temp PEM path is in the state directory."""
        with patch("agdt_ai_helpers.cli.jira.helpers.get_state_dir") as mock_state_dir:
            mock_state_dir.return_value = Path("/mock/state/dir")
            result = jira_helpers._get_temp_jira_pem_path()
            assert result == Path("/mock/state/dir/jira_ca_bundle.pem")
