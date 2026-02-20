"""
Tests for Jira CLI commands (create_epic, create_issue, create_subtask, add_comment, get_issue).

These tests validate the command-line interface functions that create and manage Jira issues.
They use mocked API calls to avoid network dependencies.
"""

from unittest.mock import MagicMock, patch

import pytest

from agdt_ai_helpers import state
from agdt_ai_helpers.cli import jira
from agdt_ai_helpers.cli.jira import (
    comment_commands,
    create_commands,
    get_commands,
)


@pytest.fixture
def temp_state_dir(tmp_path):
    """Create a temporary directory for state files."""
    with patch.object(state, "get_state_dir", return_value=tmp_path):
        yield tmp_path


@pytest.fixture
def clear_state_before(temp_state_dir):
    """Clear state before each test."""
    state.clear_state()
    yield


@pytest.fixture
def mock_jira_env():
    """Set up environment for Jira API calls."""
    with patch.dict("os.environ", {"JIRA_COPILOT_PAT": "test-token"}):
        yield


@pytest.fixture
def mock_requests_module():
    """Mock the requests module for API calls."""
    mock_module = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {"key": "DFLY-9999", "id": "12345"}
    mock_response.raise_for_status = MagicMock()
    mock_module.post.return_value = mock_response
    mock_module.get.return_value = mock_response
    # Patch in all implementation modules where _get_requests is imported
    with patch.object(create_commands, "_get_requests", return_value=mock_module):
        with patch.object(comment_commands, "_get_requests", return_value=mock_module):
            with patch.object(get_commands, "_get_requests", return_value=mock_module):
                yield mock_module


class TestCreateEpicDryRun:
    """Tests for create_epic command in dry run mode."""

    def test_create_epic_dry_run(self, temp_state_dir, clear_state_before, capsys):
        """Test create_epic in dry run mode."""
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
        jira.set_jira_value("epic_name", "TEST")
        jira.set_jira_value("role", "dev")
        jira.set_jira_value("desired_outcome", "feature")
        jira.set_jira_value("benefit", "value")

        with pytest.raises(SystemExit) as exc_info:
            jira.create_epic()
        assert exc_info.value.code == 1

    def test_create_epic_missing_epic_name(self, temp_state_dir, clear_state_before):
        """Test create_epic fails with missing epic_name."""
        jira.set_jira_value("summary", "Test")
        jira.set_jira_value("role", "dev")
        jira.set_jira_value("desired_outcome", "feature")
        jira.set_jira_value("benefit", "value")

        with pytest.raises(SystemExit) as exc_info:
            jira.create_epic()
        assert exc_info.value.code == 1

    def test_create_epic_missing_role(self, temp_state_dir, clear_state_before):
        """Test create_epic fails with missing role."""
        jira.set_jira_value("summary", "Test")
        jira.set_jira_value("epic_name", "TEST")
        jira.set_jira_value("desired_outcome", "feature")
        jira.set_jira_value("benefit", "value")

        with pytest.raises(SystemExit) as exc_info:
            jira.create_epic()
        assert exc_info.value.code == 1

    def test_create_epic_missing_desired_outcome(self, temp_state_dir, clear_state_before):
        """Test create_epic fails with missing desired_outcome."""
        jira.set_jira_value("summary", "Test")
        jira.set_jira_value("epic_name", "TEST")
        jira.set_jira_value("role", "dev")
        jira.set_jira_value("benefit", "value")

        with pytest.raises(SystemExit) as exc_info:
            jira.create_epic()
        assert exc_info.value.code == 1

    def test_create_epic_missing_benefit(self, temp_state_dir, clear_state_before):
        """Test create_epic fails with missing benefit."""
        jira.set_jira_value("summary", "Test")
        jira.set_jira_value("epic_name", "TEST")
        jira.set_jira_value("role", "dev")
        jira.set_jira_value("desired_outcome", "feature")

        with pytest.raises(SystemExit) as exc_info:
            jira.create_epic()
        assert exc_info.value.code == 1



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

