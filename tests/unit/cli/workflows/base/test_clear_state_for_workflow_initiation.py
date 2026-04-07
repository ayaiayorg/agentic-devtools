"""Tests for clear_state_for_workflow_initiation function."""

from unittest.mock import patch

from agentic_devtools import state
from agentic_devtools.cli.workflows.base import clear_state_for_workflow_initiation


class TestClearStateForWorkflowInitiation:
    """Tests for clear_state_for_workflow_initiation function."""

    def test_deletes_workflow_key(self, temp_state_dir, capsys):
        """Should remove 'workflow' key from state."""
        state.set_value("workflow", {"name": "test", "step": "init"})
        clear_state_for_workflow_initiation()

        assert state.get_value("workflow") is None

    def test_deletes_agdt_run_id_key(self, temp_state_dir, capsys):
        """Should remove 'agdt_run_id' key from state."""
        state.set_value("agdt_run_id", "abc123")
        clear_state_for_workflow_initiation()

        assert state.get_value("agdt_run_id") is None

    def test_preserves_context_keys(self, temp_state_dir, capsys):
        """Should preserve context keys like pull_request_id and jira.issue_key."""
        state.set_value("pull_request_id", 12345)
        state.set_value("jira.issue_key", "PROJECT-100")
        state.set_value("versionControl.currentBranch", "feature/branch")
        state.set_value("workflow", {"name": "test"})
        state.set_value("agdt_run_id", "abc123")

        clear_state_for_workflow_initiation()

        assert state.get_value("pull_request_id") == 12345
        assert state.get_value("jira.issue_key") == "PROJECT-100"
        assert state.get_value("versionControl.currentBranch") == "feature/branch"

    def test_does_not_call_clear_state(self, temp_state_dir, capsys):
        """Should NOT call clear_state() — no destructive clearing."""
        with patch("agentic_devtools.state.clear_state") as mock_clear:
            clear_state_for_workflow_initiation()

        mock_clear.assert_not_called()

    def test_only_deletes_expected_keys(self, temp_state_dir, capsys):
        """Should delete exactly workflow and agdt_run_id, nothing else."""
        state.set_value("workflow", {"name": "test"})
        state.set_value("agdt_run_id", "abc123")
        state.set_value("other_key", "should_survive")

        clear_state_for_workflow_initiation()

        assert state.get_value("workflow") is None
        assert state.get_value("agdt_run_id") is None
        assert state.get_value("other_key") == "should_survive"

    def test_single_save_cycle(self, temp_state_dir, capsys):
        """Should perform at most one save_state call (single I/O cycle)."""
        state.set_value("workflow", {"name": "test"})
        state.set_value("agdt_run_id", "abc123")

        with patch("agentic_devtools.cli.workflows.base.save_state", wraps=state.save_state) as mock_save:
            clear_state_for_workflow_initiation()

        assert mock_save.call_count <= 1

    def test_no_save_when_keys_absent(self, temp_state_dir, capsys):
        """Should skip save_state when neither key exists."""
        with patch("agentic_devtools.cli.workflows.base.save_state") as mock_save:
            clear_state_for_workflow_initiation()

        mock_save.assert_not_called()

    def test_prints_confirmation_message(self, temp_state_dir, capsys):
        """Should print a confirmation message after resetting state."""
        clear_state_for_workflow_initiation()

        captured = capsys.readouterr()
        assert "Reset workflow tracking state" in captured.out

    def test_preserve_run_id_true_keeps_agdt_run_id(self, temp_state_dir, capsys):
        """preserve_run_id=True should preserve agdt_run_id while deleting workflow."""
        state.set_value("workflow", {"name": "test"})
        state.set_value("agdt_run_id", "pre-generated-id")

        clear_state_for_workflow_initiation(preserve_run_id=True)

        assert state.get_value("workflow") is None
        assert state.get_value("agdt_run_id") == "pre-generated-id"

    def test_preserve_run_id_false_deletes_both(self, temp_state_dir, capsys):
        """preserve_run_id=False (default) should delete both keys — backward compat."""
        state.set_value("workflow", {"name": "test"})
        state.set_value("agdt_run_id", "abc123")

        clear_state_for_workflow_initiation(preserve_run_id=False)

        assert state.get_value("workflow") is None
        assert state.get_value("agdt_run_id") is None

    def test_preserve_run_id_true_no_run_id_in_state(self, temp_state_dir, capsys):
        """preserve_run_id=True with no agdt_run_id in state should not fail."""
        state.set_value("workflow", {"name": "test"})

        clear_state_for_workflow_initiation(preserve_run_id=True)

        assert state.get_value("workflow") is None
        assert state.get_value("agdt_run_id") is None

    def test_preserve_run_id_true_preserves_other_keys(self, temp_state_dir, capsys):
        """preserve_run_id=True should preserve agdt_run_id and all other non-workflow keys."""
        state.set_value("workflow", {"name": "test"})
        state.set_value("agdt_run_id", "pre-generated-id")
        state.set_value("pull_request_id", 12345)
        state.set_value("other_key", "should_survive")

        clear_state_for_workflow_initiation(preserve_run_id=True)

        assert state.get_value("workflow") is None
        assert state.get_value("agdt_run_id") == "pre-generated-id"
        assert state.get_value("pull_request_id") == 12345
        assert state.get_value("other_key") == "should_survive"

    def test_preserve_run_id_true_single_save_cycle(self, temp_state_dir, capsys):
        """preserve_run_id=True should perform at most one save_state call."""
        state.set_value("workflow", {"name": "test"})

        with patch("agentic_devtools.cli.workflows.base.save_state", wraps=state.save_state) as mock_save:
            clear_state_for_workflow_initiation(preserve_run_id=True)

        assert mock_save.call_count <= 1
