"""Tests for vpn_on_async function."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure_devops.vpn_toggle import vpn_on_async


class TestVpnOnAsync:
    """Tests for vpn_on_async function."""

    def test_spawns_background_task(self):
        """Should spawn a background task for VPN connection."""
        mock_task = MagicMock()
        mock_task.id = "vpn-task-id"
        mock_task.command = "agdt-vpn-on"

        with patch(
            "agentic_devtools.background_tasks.run_function_in_background",
            return_value=mock_task,
        ) as mock_bg:
            with patch(
                "agentic_devtools.task_state.print_task_tracking_info"
            ):
                vpn_on_async()

        mock_bg.assert_called_once()

    def test_uses_agdt_vpn_on_command_name(self):
        """Should use 'agdt-vpn-on' as the command_display_name."""
        mock_task = MagicMock()
        mock_task.id = "vpn-task-id"
        mock_task.command = "agdt-vpn-on"

        with patch(
            "agentic_devtools.background_tasks.run_function_in_background",
            return_value=mock_task,
        ) as mock_bg:
            with patch(
                "agentic_devtools.task_state.print_task_tracking_info"
            ):
                vpn_on_async()

        call_kwargs = mock_bg.call_args[1]
        assert call_kwargs["command_display_name"] == "agdt-vpn-on"
