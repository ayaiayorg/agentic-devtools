"""Tests for clear_state_for_workflow_initiation function."""

from unittest.mock import patch

from agentic_devtools.cli.workflows.base import clear_state_for_workflow_initiation


class TestClearStateForWorkflowInitiation:
    """Tests for clear_state_for_workflow_initiation function."""

    def test_deletes_workflow_key(self, capsys):
        """Should call delete_value('workflow')."""
        with patch("agentic_devtools.cli.workflows.base.delete_value") as mock_delete:
            clear_state_for_workflow_initiation()

        mock_delete.assert_any_call("workflow")

    def test_deletes_agdt_run_id_key(self, capsys):
        """Should call delete_value('agdt_run_id')."""
        with patch("agentic_devtools.cli.workflows.base.delete_value") as mock_delete:
            clear_state_for_workflow_initiation()

        mock_delete.assert_any_call("agdt_run_id")

    def test_does_not_call_clear_state(self, capsys):
        """Should NOT call clear_state() — no destructive clearing."""
        with patch("agentic_devtools.cli.workflows.base.delete_value"):
            with patch("agentic_devtools.state.clear_state") as mock_clear:
                clear_state_for_workflow_initiation()

        mock_clear.assert_not_called()

    def test_does_not_call_clear_temp_folder(self, capsys):
        """Should NOT call clear_temp_folder() — no filesystem deletion."""
        with patch("agentic_devtools.cli.workflows.base.delete_value"):
            with patch("agentic_devtools.state.clear_temp_folder") as mock_clear_temp:
                clear_state_for_workflow_initiation()

        mock_clear_temp.assert_not_called()

    def test_only_deletes_expected_keys(self, capsys):
        """Should delete exactly workflow and agdt_run_id, nothing else."""
        with patch("agentic_devtools.cli.workflows.base.delete_value") as mock_delete:
            clear_state_for_workflow_initiation()

        assert mock_delete.call_count == 2
        deleted_keys = {call.args[0] for call in mock_delete.call_args_list}
        assert deleted_keys == {"workflow", "agdt_run_id"}

    def test_prints_confirmation_message(self, capsys):
        """Should print a confirmation message after resetting state."""
        with patch("agentic_devtools.cli.workflows.base.delete_value"):
            clear_state_for_workflow_initiation()

        captured = capsys.readouterr()
        assert "Reset workflow tracking state" in captured.out
