"""
Tests for Jira helper utilities.
"""

from pathlib import Path
from unittest.mock import patch

from agdt_ai_helpers.cli.jira import helpers as jira_helpers


class TestGetJiraPemPaths:
    """Tests for _get_repo_jira_pem_path and _get_temp_jira_pem_path helpers."""

    def test_repo_path_returns_path_in_scripts_dir(self):
        """Test that repo PEM path is in the scripts directory (parent of temp)."""
        with patch("agdt_ai_helpers.cli.jira.helpers.get_state_dir") as mock_state_dir:
            # state_dir is typically scripts/temp, so parent is scripts/
            mock_state_dir.return_value = Path("/mock/scripts/temp")
            result = jira_helpers._get_repo_jira_pem_path()
            assert result == Path("/mock/scripts/jira_ca_bundle.pem")
