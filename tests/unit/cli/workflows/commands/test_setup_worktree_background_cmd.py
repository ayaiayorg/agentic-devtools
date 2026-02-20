"""Tests for SetupWorktreeBackgroundCmd."""

from unittest.mock import patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli.workflows import commands
from agentic_devtools.prompts import loader


@pytest.fixture
def temp_state_dir(tmp_path):
    """Create a temporary directory for state files."""
    with patch.object(state, "get_state_dir", return_value=tmp_path):
        yield tmp_path


@pytest.fixture
def temp_prompts_dir(tmp_path):
    """Create a temporary prompts directory with test templates."""
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    with patch.object(loader, "get_prompts_dir", return_value=prompts_dir):
        yield prompts_dir


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create a temporary output directory."""
    output_dir = tmp_path / "temp"
    output_dir.mkdir()
    with patch.object(loader, "get_temp_output_dir", return_value=output_dir):
        yield output_dir


@pytest.fixture
def clear_state_before(temp_state_dir):
    """Clear state before each test.

    Note: We only remove the state file, not the entire temp folder,
    to avoid deleting directories created by other fixtures (like temp_prompts_dir).
    """
    state_file = temp_state_dir / "agdt-state.json"
    if state_file.exists():
        state_file.unlink()
    yield


@pytest.fixture
def mock_workflow_state_clearing():
    """Mock clear_state_for_workflow_initiation to be a no-op.

    This is needed because workflow initiation commands clear all state at the start,
    but tests set up state before calling the command. Without this mock, the test's
    state setup would be wiped immediately.
    """
    with patch("agentic_devtools.cli.workflows.commands.clear_state_for_workflow_initiation"):
        yield


class TestSetupWorktreeBackgroundCmd:
    """Tests for setup_worktree_background_cmd function."""

    def test_basic_invocation(self, temp_state_dir, clear_state_before):
        """Test basic command invocation with required args."""
        with patch("agentic_devtools.cli.workflows.worktree_setup.setup_worktree_in_background_sync") as mock_setup:
            commands.setup_worktree_background_cmd(_argv=["--issue-key", "DFLY-1234"])

        mock_setup.assert_called_once_with(
            issue_key="DFLY-1234",
            branch_prefix="feature",
            workflow_name="work-on-jira-issue",
            user_request=None,
            additional_params=None,
        )

    def test_with_all_options(self, temp_state_dir, clear_state_before):
        """Test command with all options provided."""
        with patch("agentic_devtools.cli.workflows.worktree_setup.setup_worktree_in_background_sync") as mock_setup:
            commands.setup_worktree_background_cmd(
                _argv=[
                    "--issue-key",
                    "DFLY-1234",
                    "--branch-prefix",
                    "bugfix",
                    "--workflow-name",
                    "custom-workflow",
                    "--user-request",
                    "My request",
                    "--additional-params",
                    '{"key": "value"}',
                ]
            )

        mock_setup.assert_called_once_with(
            issue_key="DFLY-1234",
            branch_prefix="bugfix",
            workflow_name="custom-workflow",
            user_request="My request",
            additional_params={"key": "value"},
        )

    def test_with_invalid_json_params(self, temp_state_dir, clear_state_before, capsys):
        """Test command handles invalid JSON in additional-params."""
        with patch("agentic_devtools.cli.workflows.worktree_setup.setup_worktree_in_background_sync") as mock_setup:
            commands.setup_worktree_background_cmd(
                _argv=[
                    "--issue-key",
                    "DFLY-1234",
                    "--additional-params",
                    "not-valid-json",
                ]
            )

        # Should still call setup but with None for additional_params
        mock_setup.assert_called_once()
        call_kwargs = mock_setup.call_args[1]
        assert call_kwargs["additional_params"] is None

        captured = capsys.readouterr()
        assert "Could not parse additional-params JSON" in captured.err
