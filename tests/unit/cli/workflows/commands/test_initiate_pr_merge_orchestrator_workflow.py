"""Tests for initiate_pr_merge_orchestrator_workflow."""

from unittest.mock import patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli.workflows import commands
from agentic_devtools.prompts import loader


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
    """Clear state before each test."""
    state_file = temp_state_dir / "state.json"
    if state_file.exists():
        state_file.unlink()
    yield


@pytest.fixture
def mock_workflow_init():
    """Mock initiate_workflow to avoid template loading."""
    with patch("agentic_devtools.cli.workflows.commands.initiate_workflow") as mock:
        mock.return_value = "rendered prompt"
        yield mock


class TestInitiatePrMergeOrchestratorWorkflow:
    """Tests for initiate_pr_merge_orchestrator_workflow."""

    def test_missing_pull_request_id_exits(self, temp_state_dir, clear_state_before, capsys):
        """Test error when --pull-request-id is not provided."""
        with pytest.raises(SystemExit) as exc_info:
            commands.initiate_pr_merge_orchestrator_workflow(_argv=[])
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "--pull-request-id is required" in captured.err

    def test_poll_interval_below_minimum_exits(self, temp_state_dir, clear_state_before, capsys):
        """Test error when poll-interval-seconds is below 10."""
        with pytest.raises(SystemExit) as exc_info:
            commands.initiate_pr_merge_orchestrator_workflow(
                _argv=["--pull-request-id", "123", "--poll-interval-seconds", "5"]
            )
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "at least 10" in captured.err

    def test_default_values(self, temp_state_dir, clear_state_before, mock_workflow_init):
        """Test that default values are applied when no optional args provided."""
        commands.initiate_pr_merge_orchestrator_workflow(_argv=["--pull-request-id", "123"])

        mock_workflow_init.assert_called_once()
        call_kwargs = mock_workflow_init.call_args[1]
        assert call_kwargs["workflow_name"] == "pr-merge-orchestrator"
        context = call_kwargs["context"]
        assert context["pull_request_id"] == "123"
        assert context["strategy"] == "squash"
        assert context["delete_branch"] is True
        assert context["poll_interval_seconds"] == 30
        assert context["max_cycles"] == 120
        assert context["auto_merge"] is False
        assert context["cycle_count"] == 0
        assert context["last_processed_head_sha"] is None
        assert context["last_processed_review_id"] is None

    def test_custom_strategy(self, temp_state_dir, clear_state_before, mock_workflow_init):
        """Test merge strategy can be customized."""
        commands.initiate_pr_merge_orchestrator_workflow(_argv=["--pull-request-id", "456", "--strategy", "rebase"])

        call_kwargs = mock_workflow_init.call_args[1]
        assert call_kwargs["context"]["strategy"] == "rebase"

    def test_custom_poll_interval(self, temp_state_dir, clear_state_before, mock_workflow_init):
        """Test poll interval can be customized."""
        commands.initiate_pr_merge_orchestrator_workflow(
            _argv=["--pull-request-id", "789", "--poll-interval-seconds", "60"]
        )

        call_kwargs = mock_workflow_init.call_args[1]
        assert call_kwargs["context"]["poll_interval_seconds"] == 60

    def test_custom_max_cycles(self, temp_state_dir, clear_state_before, mock_workflow_init):
        """Test max cycles can be customized."""
        commands.initiate_pr_merge_orchestrator_workflow(_argv=["--pull-request-id", "789", "--max-cycles", "50"])

        call_kwargs = mock_workflow_init.call_args[1]
        assert call_kwargs["context"]["max_cycles"] == 50

    def test_auto_merge_true(self, temp_state_dir, clear_state_before, mock_workflow_init):
        """Test auto-merge flag can be set to true."""
        commands.initiate_pr_merge_orchestrator_workflow(_argv=["--pull-request-id", "100", "--auto-merge", "true"])

        call_kwargs = mock_workflow_init.call_args[1]
        assert call_kwargs["context"]["auto_merge"] is True

    def test_delete_branch_false(self, temp_state_dir, clear_state_before, mock_workflow_init):
        """Test delete-branch flag can be set to false."""
        commands.initiate_pr_merge_orchestrator_workflow(_argv=["--pull-request-id", "100", "--delete-branch", "false"])

        call_kwargs = mock_workflow_init.call_args[1]
        assert call_kwargs["context"]["delete_branch"] is False

    def test_state_values_persisted(self, temp_state_dir, clear_state_before, mock_workflow_init):
        """Test that configuration values are persisted in state."""
        commands.initiate_pr_merge_orchestrator_workflow(_argv=["--pull-request-id", "999", "--strategy", "merge"])

        assert state.get_value("pull_request_id") == "999"
        assert state.get_value("merge.strategy") == "merge"
        assert state.get_value("merge.delete_branch") is True
        assert state.get_value("merge.poll_interval_seconds") == 30
        assert state.get_value("merge.max_cycles") == 120
        assert state.get_value("merge.auto_merge") is False

    def test_programmatic_params_override_cli(self, temp_state_dir, clear_state_before, mock_workflow_init):
        """Test that programmatic parameters take precedence over CLI."""
        commands.initiate_pr_merge_orchestrator_workflow(
            pull_request_id="42",
            strategy="rebase",
            max_cycles=10,
        )

        call_kwargs = mock_workflow_init.call_args[1]
        assert call_kwargs["context"]["pull_request_id"] == "42"
        assert call_kwargs["context"]["strategy"] == "rebase"
        assert call_kwargs["context"]["max_cycles"] == 10

    def test_required_state_keys(self, temp_state_dir, clear_state_before, mock_workflow_init):
        """Test that required_state_keys includes pull_request_id."""
        commands.initiate_pr_merge_orchestrator_workflow(_argv=["--pull-request-id", "1"])

        call_kwargs = mock_workflow_init.call_args[1]
        assert "pull_request_id" in call_kwargs["required_state_keys"]

    def test_optional_state_keys(self, temp_state_dir, clear_state_before, mock_workflow_init):
        """Test that optional_state_keys includes merge config keys."""
        commands.initiate_pr_merge_orchestrator_workflow(_argv=["--pull-request-id", "1"])

        call_kwargs = mock_workflow_init.call_args[1]
        optional = call_kwargs["optional_state_keys"]
        assert "merge.strategy" in optional
        assert "merge.delete_branch" in optional
        assert "merge.poll_interval_seconds" in optional
        assert "merge.max_cycles" in optional
        assert "merge.auto_merge" in optional

    def test_invalid_strategy_rejected(self, temp_state_dir, clear_state_before):
        """Test that an invalid strategy value is rejected by argparse."""
        with pytest.raises(SystemExit):
            commands.initiate_pr_merge_orchestrator_workflow(_argv=["--pull-request-id", "1", "--strategy", "invalid"])
