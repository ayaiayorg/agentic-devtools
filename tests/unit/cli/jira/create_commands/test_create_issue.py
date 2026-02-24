"""Tests for create_issue CLI command."""

from unittest.mock import MagicMock, patch

import pytest

from agdt_ai_helpers.cli import jira
from agdt_ai_helpers.cli.jira import create_commands


class TestCreateIssueDryRun:
    """Tests for create_issue command in dry run mode."""

    def test_create_issue_dry_run(self, temp_state_dir, clear_state_before, capsys):
        """Test create_issue in dry run mode."""
        jira.set_jira_value("summary", "Test Issue")
        jira.set_jira_value("role", "developer")
        jira.set_jira_value("desired_outcome", "functionality")
        jira.set_jira_value("benefit", "value")
        jira.set_jira_value("dry_run", True)

        jira.create_issue()

        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "Test Issue" in captured.out

    def test_create_issue_custom_type(self, temp_state_dir, clear_state_before, capsys):
        """Test create_issue with custom issue type."""
        jira.set_jira_value("summary", "Test Bug")
        jira.set_jira_value("issue_type", "Bug")
        jira.set_jira_value("role", "tester")
        jira.set_jira_value("desired_outcome", "bug fix")
        jira.set_jira_value("benefit", "stability")
        jira.set_jira_value("dry_run", True)

        jira.create_issue()

        captured = capsys.readouterr()
        assert "Bug" in captured.out

    def test_create_issue_missing_summary(self, temp_state_dir, clear_state_before):
        """Test create_issue fails with missing summary."""
        jira.set_jira_value("role", "dev")
        jira.set_jira_value("desired_outcome", "feature")
        jira.set_jira_value("benefit", "value")

        with pytest.raises(SystemExit) as exc_info:
            jira.create_issue()
        assert exc_info.value.code == 1

    def test_create_issue_missing_role(self, temp_state_dir, clear_state_before):
        """Test create_issue fails with missing role."""
        jira.set_jira_value("summary", "Test")
        jira.set_jira_value("desired_outcome", "feature")
        jira.set_jira_value("benefit", "value")

        with pytest.raises(SystemExit) as exc_info:
            jira.create_issue()
        assert exc_info.value.code == 1

    def test_create_issue_missing_desired_outcome(self, temp_state_dir, clear_state_before):
        """Test create_issue fails with missing desired_outcome."""
        jira.set_jira_value("summary", "Test")
        jira.set_jira_value("role", "dev")
        jira.set_jira_value("benefit", "value")

        with pytest.raises(SystemExit) as exc_info:
            jira.create_issue()
        assert exc_info.value.code == 1

    def test_create_issue_missing_benefit(self, temp_state_dir, clear_state_before):
        """Test create_issue fails with missing benefit."""
        jira.set_jira_value("summary", "Test")
        jira.set_jira_value("role", "dev")
        jira.set_jira_value("desired_outcome", "feature")

        with pytest.raises(SystemExit) as exc_info:
            jira.create_issue()
        assert exc_info.value.code == 1


class TestCreateIssueWithMock:
    """Tests for create_issue with mocked API calls."""

    def test_create_issue_success(
        self,
        temp_state_dir,
        clear_state_before,
        mock_jira_env,
        mock_requests_module,
        capsys,
    ):
        """Test successful issue creation."""
        jira.set_jira_value("summary", "Test Issue")
        jira.set_jira_value("role", "developer")
        jira.set_jira_value("desired_outcome", "feature")
        jira.set_jira_value("benefit", "value")

        jira.create_issue()

        captured = capsys.readouterr()
        assert "DFLY-9999" in captured.out
        assert "created successfully" in captured.out

    def test_create_issue_api_error(self, temp_state_dir, clear_state_before, mock_jira_env):
        """Test create_issue handles API error."""
        jira.set_jira_value("summary", "Test Issue")
        jira.set_jira_value("role", "developer")
        jira.set_jira_value("desired_outcome", "feature")
        jira.set_jira_value("benefit", "value")

        mock_module = MagicMock()
        mock_module.post.side_effect = Exception("API Error")
        with patch.object(create_commands, "_get_requests", return_value=mock_module):
            with pytest.raises(SystemExit) as exc_info:
                jira.create_issue()
            assert exc_info.value.code == 1
