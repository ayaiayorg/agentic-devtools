"""Tests for SetupWorktreeFromState."""

from unittest.mock import patch

import pytest


class TestSetupWorktreeFromState:
    """Tests for _setup_worktree_from_state function."""

    @patch("agentic_devtools.cli.workflows.worktree_setup.setup_worktree_in_background_sync")
    @patch("agentic_devtools.state.get_value")
    def test_reads_parameters_from_state(self, mock_get_value, mock_setup_sync):
        """Test that parameters are read from state correctly."""
        mock_get_value.side_effect = lambda key: {
            "worktree_setup.issue_key": "DFLY-5678",
            "worktree_setup.branch_prefix": "bugfix",
            "worktree_setup.branch_name": "feature/DFLY-5678/test",
            "worktree_setup.use_existing_branch": "true",
            "worktree_setup.workflow_name": "pull-request-review",
            "worktree_setup.user_request": "Review this PR",
            "worktree_setup.additional_params": '{"pr_id": "123"}',
            "worktree_setup.auto_execute_command": None,
            "worktree_setup.auto_execute_timeout": None,
        }.get(key)

        from agentic_devtools.cli.workflows.worktree_setup import _setup_worktree_from_state

        _setup_worktree_from_state()

        mock_setup_sync.assert_called_once_with(
            issue_key="DFLY-5678",
            branch_prefix="bugfix",
            branch_name="feature/DFLY-5678/test",
            use_existing_branch=True,
            workflow_name="pull-request-review",
            user_request="Review this PR",
            additional_params={"pr_id": "123"},
            auto_execute_command=None,
            auto_execute_timeout=300,
        )

    @patch("agentic_devtools.state.get_value")
    def test_raises_error_when_issue_key_missing(self, mock_get_value):
        """Test that ValueError is raised when issue_key is missing."""
        mock_get_value.return_value = None

        from agentic_devtools.cli.workflows.worktree_setup import _setup_worktree_from_state

        with pytest.raises(ValueError, match="worktree_setup.issue_key not set"):
            _setup_worktree_from_state()

    @patch("agentic_devtools.cli.workflows.worktree_setup.setup_worktree_in_background_sync")
    @patch("agentic_devtools.state.get_value")
    def test_handles_invalid_json_in_additional_params(self, mock_get_value, mock_setup_sync):
        """Test that invalid JSON in additional_params is handled gracefully."""
        mock_get_value.side_effect = lambda key: {
            "worktree_setup.issue_key": "DFLY-1234",
            "worktree_setup.branch_prefix": "feature",
            "worktree_setup.branch_name": None,
            "worktree_setup.use_existing_branch": "false",
            "worktree_setup.workflow_name": "work-on-jira-issue",
            "worktree_setup.user_request": None,
            "worktree_setup.additional_params": "invalid json {",
            "worktree_setup.auto_execute_command": None,
            "worktree_setup.auto_execute_timeout": None,
        }.get(key)

        from agentic_devtools.cli.workflows.worktree_setup import _setup_worktree_from_state

        _setup_worktree_from_state()

        mock_setup_sync.assert_called_once()
        call_kwargs = mock_setup_sync.call_args[1]
        assert call_kwargs["additional_params"] is None

    @patch("agentic_devtools.cli.workflows.worktree_setup.setup_worktree_in_background_sync")
    @patch("agentic_devtools.state.get_value")
    def test_uses_default_values_when_not_set(self, mock_get_value, mock_setup_sync):
        """Test that default values are used when state values are not set."""
        mock_get_value.side_effect = lambda key: {
            "worktree_setup.issue_key": "DFLY-9999",
            "worktree_setup.branch_prefix": None,  # Should default to "feature"
            "worktree_setup.branch_name": None,
            "worktree_setup.use_existing_branch": None,  # Should default to False
            "worktree_setup.workflow_name": None,  # Should default to "work-on-jira-issue"
            "worktree_setup.user_request": None,
            "worktree_setup.additional_params": None,
            "worktree_setup.auto_execute_command": None,
            "worktree_setup.auto_execute_timeout": None,
        }.get(key)

        from agentic_devtools.cli.workflows.worktree_setup import _setup_worktree_from_state

        _setup_worktree_from_state()

        mock_setup_sync.assert_called_once_with(
            issue_key="DFLY-9999",
            branch_prefix="feature",
            branch_name=None,
            use_existing_branch=False,
            workflow_name="work-on-jira-issue",
            user_request=None,
            additional_params=None,
            auto_execute_command=None,
            auto_execute_timeout=300,
        )

    @patch("agentic_devtools.cli.workflows.worktree_setup.setup_worktree_in_background_sync")
    @patch("agentic_devtools.state.get_value")
    def test_reads_auto_execute_command_from_state(self, mock_get_value, mock_setup_sync):
        """Test that auto_execute_command is read from state as JSON list."""
        mock_get_value.side_effect = lambda key: {
            "worktree_setup.issue_key": "DFLY-1234",
            "worktree_setup.branch_prefix": "feature",
            "worktree_setup.branch_name": None,
            "worktree_setup.use_existing_branch": None,
            "worktree_setup.workflow_name": "pull-request-review",
            "worktree_setup.user_request": None,
            "worktree_setup.additional_params": None,
            "worktree_setup.auto_execute_command": '["agdt-review", "--pr-id", "42"]',
            "worktree_setup.auto_execute_timeout": "120",
        }.get(key)

        from agentic_devtools.cli.workflows.worktree_setup import _setup_worktree_from_state

        _setup_worktree_from_state()

        call_kwargs = mock_setup_sync.call_args[1]
        assert call_kwargs["auto_execute_command"] == ["agdt-review", "--pr-id", "42"]
        assert call_kwargs["auto_execute_timeout"] == 120

    @patch("agentic_devtools.cli.workflows.worktree_setup.setup_worktree_in_background_sync")
    @patch("agentic_devtools.state.get_value")
    def test_handles_invalid_json_in_auto_execute_command(self, mock_get_value, mock_setup_sync):
        """Test that invalid JSON in auto_execute_command is handled gracefully."""
        mock_get_value.side_effect = lambda key: {
            "worktree_setup.issue_key": "DFLY-1234",
            "worktree_setup.branch_prefix": "feature",
            "worktree_setup.branch_name": None,
            "worktree_setup.use_existing_branch": None,
            "worktree_setup.workflow_name": "work-on-jira-issue",
            "worktree_setup.user_request": None,
            "worktree_setup.additional_params": None,
            "worktree_setup.auto_execute_command": "not valid json [",
            "worktree_setup.auto_execute_timeout": None,
        }.get(key)

        from agentic_devtools.cli.workflows.worktree_setup import _setup_worktree_from_state

        _setup_worktree_from_state()

        call_kwargs = mock_setup_sync.call_args[1]
        assert call_kwargs["auto_execute_command"] is None

    @patch("agentic_devtools.cli.workflows.worktree_setup.setup_worktree_in_background_sync")
    @patch("agentic_devtools.state.get_value")
    def test_handles_invalid_int_in_auto_execute_timeout(self, mock_get_value, mock_setup_sync):
        """Test that invalid integer in auto_execute_timeout defaults to 300."""
        mock_get_value.side_effect = lambda key: {
            "worktree_setup.issue_key": "DFLY-1234",
            "worktree_setup.branch_prefix": "feature",
            "worktree_setup.branch_name": None,
            "worktree_setup.use_existing_branch": None,
            "worktree_setup.workflow_name": "work-on-jira-issue",
            "worktree_setup.user_request": None,
            "worktree_setup.additional_params": None,
            "worktree_setup.auto_execute_command": None,
            "worktree_setup.auto_execute_timeout": "not-a-number",
        }.get(key)

        from agentic_devtools.cli.workflows.worktree_setup import _setup_worktree_from_state

        _setup_worktree_from_state()

        call_kwargs = mock_setup_sync.call_args[1]
        assert call_kwargs["auto_execute_timeout"] == 300
