"""
Tests for Jira helper utilities.
"""

from pathlib import Path
from unittest.mock import patch

from agentic_devtools.cli.jira import helpers as jira_helpers


class TestGetJiraPemPaths:
    """Tests for _get_repo_jira_pem_path and _get_temp_jira_pem_path helpers."""

    def test_repo_path_returns_path_in_scripts_dir(self):
        """Test that repo PEM path is in the scripts directory via git root."""
        with patch("agentic_devtools.cli.jira.helpers._get_git_repo_root") as mock_git_root:
            mock_git_root.return_value = Path("/mock/repo")
            result = jira_helpers._get_repo_jira_pem_path()
            assert result == Path("/mock/repo/scripts/jira_ca_bundle.pem")

    def test_repo_path_falls_back_to_state_dir_when_no_git_root(self, tmp_path):
        """Test fallback to state dir when not in a git repo."""
        state_dir = tmp_path / "state"
        state_dir.mkdir()
        with patch("agentic_devtools.cli.jira.helpers._get_git_repo_root", return_value=None):
            with patch("agentic_devtools.cli.jira.helpers.get_state_dir", return_value=state_dir):
                result = jira_helpers._get_repo_jira_pem_path()
                assert result == state_dir / "jira_ca_bundle.pem"
