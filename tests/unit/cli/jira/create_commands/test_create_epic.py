"""Tests for create_epic CLI command."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli import jira
from agentic_devtools.cli.jira import create_commands


class TestCreateEpicDryRun:
    """Tests for create_epic command in dry run mode."""

    def test_create_epic_dry_run(self, temp_state_dir, clear_state_before, capsys):
        """Test create_epic in dry run mode."""
        jira.set_jira_value("project_key", "TESTPROJ")
        jira.set_jira_value("summary", "Test Epic")
        jira.set_jira_value("epic_name", "TEST-EPIC")
        jira.set_jira_value("role", "developer")
        jira.set_jira_value("desired_outcome", "test functionality")
        jira.set_jira_value("benefit", "test coverage")
        jira.set_jira_value("dry_run", True)

        jira.create_epic()

        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "Test Epic" in captured.out
        assert "TEST-EPIC" in captured.out

    def test_create_epic_missing_summary(self, temp_state_dir, clear_state_before):
        """Test create_epic fails with missing summary."""
        jira.set_jira_value("project_key", "TESTPROJ")
        jira.set_jira_value("epic_name", "TEST")
        jira.set_jira_value("role", "dev")
        jira.set_jira_value("desired_outcome", "feature")
        jira.set_jira_value("benefit", "value")

        with pytest.raises(SystemExit) as exc_info:
            jira.create_epic()
        assert exc_info.value.code == 1

    def test_create_epic_missing_epic_name(self, temp_state_dir, clear_state_before):
        """Test create_epic fails with missing epic_name."""
        jira.set_jira_value("project_key", "TESTPROJ")
        jira.set_jira_value("summary", "Test")
        jira.set_jira_value("role", "dev")
        jira.set_jira_value("desired_outcome", "feature")
        jira.set_jira_value("benefit", "value")

        with pytest.raises(SystemExit) as exc_info:
            jira.create_epic()
        assert exc_info.value.code == 1

    def test_create_epic_missing_role(self, temp_state_dir, clear_state_before):
        """Test create_epic fails with missing role."""
        jira.set_jira_value("project_key", "TESTPROJ")
        jira.set_jira_value("summary", "Test")
        jira.set_jira_value("epic_name", "TEST")
        jira.set_jira_value("desired_outcome", "feature")
        jira.set_jira_value("benefit", "value")

        with pytest.raises(SystemExit) as exc_info:
            jira.create_epic()
        assert exc_info.value.code == 1

    def test_create_epic_missing_desired_outcome(self, temp_state_dir, clear_state_before):
        """Test create_epic fails with missing desired_outcome."""
        jira.set_jira_value("project_key", "TESTPROJ")
        jira.set_jira_value("summary", "Test")
        jira.set_jira_value("epic_name", "TEST")
        jira.set_jira_value("role", "dev")
        jira.set_jira_value("benefit", "value")

        with pytest.raises(SystemExit) as exc_info:
            jira.create_epic()
        assert exc_info.value.code == 1

    def test_create_epic_missing_benefit(self, temp_state_dir, clear_state_before):
        """Test create_epic fails with missing benefit."""
        jira.set_jira_value("project_key", "TESTPROJ")
        jira.set_jira_value("summary", "Test")
        jira.set_jira_value("epic_name", "TEST")
        jira.set_jira_value("role", "dev")
        jira.set_jira_value("desired_outcome", "feature")

        with pytest.raises(SystemExit) as exc_info:
            jira.create_epic()
        assert exc_info.value.code == 1

    def test_create_epic_missing_project_key(self, temp_state_dir, clear_state_before, capsys):
        """Test create_epic fails with missing project_key and no configured keys."""
        jira.set_jira_value("summary", "Test")
        jira.set_jira_value("epic_name", "TEST")
        jira.set_jira_value("role", "dev")
        jira.set_jira_value("desired_outcome", "feature")
        jira.set_jira_value("benefit", "value")

        with patch.object(create_commands, "get_jira_project_keys", return_value=[]):
            with pytest.raises(SystemExit) as exc_info:
                jira.create_epic()
            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "No Jira project key configured" in captured.err

    def test_create_epic_uses_configured_project_key(self, temp_state_dir, clear_state_before, capsys):
        """Test create_epic falls back to configured project keys when jira.project_key is not set."""
        jira.set_jira_value("summary", "Test Epic")
        jira.set_jira_value("epic_name", "TEST-EPIC")
        jira.set_jira_value("role", "dev")
        jira.set_jira_value("desired_outcome", "feature")
        jira.set_jira_value("benefit", "value")
        jira.set_jira_value("dry_run", True)

        with patch.object(create_commands, "get_jira_project_keys", return_value=["PROJ"]):
            jira.create_epic()

        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out


class TestCreateEpicWithMock:
    """Tests for create_epic with mocked API calls."""

    def test_create_epic_success(
        self,
        temp_state_dir,
        clear_state_before,
        mock_jira_env,
        mock_requests_module,
        capsys,
    ):
        """Test successful epic creation."""
        jira.set_jira_value("project_key", "TESTPROJ")
        jira.set_jira_value("summary", "Test Epic")
        jira.set_jira_value("epic_name", "TEST-EPIC")
        jira.set_jira_value("role", "developer")
        jira.set_jira_value("desired_outcome", "test functionality")
        jira.set_jira_value("benefit", "test coverage")

        jira.create_epic()

        captured = capsys.readouterr()
        assert "DFLY-9999" in captured.out
        assert "Epic created successfully" in captured.out

    def test_create_epic_api_error(self, temp_state_dir, clear_state_before, mock_jira_env):
        """Test create_epic handles API error."""
        jira.set_jira_value("project_key", "TESTPROJ")
        jira.set_jira_value("summary", "Test Epic")
        jira.set_jira_value("epic_name", "TEST-EPIC")
        jira.set_jira_value("role", "developer")
        jira.set_jira_value("desired_outcome", "test")
        jira.set_jira_value("benefit", "test")

        mock_module = MagicMock()
        mock_module.post.side_effect = Exception("API Error")
        with patch.object(create_commands, "_get_requests", return_value=mock_module):
            with pytest.raises(SystemExit) as exc_info:
                jira.create_epic()
            assert exc_info.value.code == 1
