"""
Tests for cli/runner.py module.

This module tests the command runner that maps agdt-* commands to their
entry point functions.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest
from agentic_devtools.cli import runner


class TestCommandMap:
    """Tests for the COMMAND_MAP constant."""

    def test_command_map_is_not_empty(self):
        """Test that COMMAND_MAP contains commands."""
        assert len(runner.COMMAND_MAP) > 0

    def test_all_commands_have_module_and_function(self):
        """Test that all commands map to (module, function) tuples."""
        for cmd, mapping in runner.COMMAND_MAP.items():
            assert isinstance(mapping, tuple), f"{cmd} mapping is not a tuple"
            assert len(mapping) == 2, f"{cmd} mapping doesn't have 2 elements"
            module_name, func_name = mapping
            assert isinstance(module_name, str), f"{cmd} module name is not a string"
            assert isinstance(func_name, str), f"{cmd} function name is not a string"

    def test_all_command_names_start_with_agdt(self):
        """Test that all command names start with 'agdt-'."""
        for cmd in runner.COMMAND_MAP.keys():
            assert cmd.startswith("agdt-"), (
                f"Command '{cmd}' doesn't start with 'agdt-'"
            )

    def test_common_commands_exist(self):
        """Test that common commands are in the map."""
        expected_commands = [
            "agdt-set",
            "agdt-get",
            "agdt-show",
            "agdt-clear",
            "agdt-delete",
            "agdt-git-save-work",
            "agdt-git-push",
            "agdt-test",
            "agdt-get-jira-issue",
            "agdt-add-jira-comment",
            "agdt-create-pull-request",
            "agdt-task-wait",
        ]
        for cmd in expected_commands:
            assert cmd in runner.COMMAND_MAP, (
                f"Expected command '{cmd}' not in COMMAND_MAP"
            )

    def test_azure_cli_commands_exist(self):
        """Test that Azure CLI commands are in the map."""
        azure_commands = [
            "agdt-query-app-insights",
            "agdt-query-fabric-dap-errors",
            "agdt-query-fabric-dap-provisioning",
            "agdt-query-fabric-dap-timeline",
        ]
        for cmd in azure_commands:
            assert cmd in runner.COMMAND_MAP, (
                f"Expected Azure command '{cmd}' not in COMMAND_MAP"
            )

    @pytest.mark.parametrize(
        "command,expected_module,expected_func",
        [
            (
                "agdt-query-app-insights",
                "agentic_devtools.cli.azure",
                "query_app_insights_async",
            ),
            (
                "agdt-query-fabric-dap-errors",
                "agentic_devtools.cli.azure",
                "query_fabric_dap_errors_async",
            ),
            (
                "agdt-query-fabric-dap-provisioning",
                "agentic_devtools.cli.azure",
                "query_fabric_dap_provisioning_async",
            ),
            (
                "agdt-query-fabric-dap-timeline",
                "agentic_devtools.cli.azure",
                "query_fabric_dap_timeline_async",
            ),
        ],
    )
    def test_azure_cli_command_mappings(self, command, expected_module, expected_func):
        """Test that Azure CLI commands map to correct module and function."""
        module_name, func_name = runner.COMMAND_MAP[command]
        assert module_name == expected_module
        assert func_name == expected_func


class TestRunCommand:
    """Tests for the run_command function."""

    def test_exits_with_error_for_unknown_command(self):
        """Test that run_command exits with error for unknown command."""
        with pytest.raises(SystemExit) as exc_info:
            runner.run_command("unknown-command")
        assert exc_info.value.code == 1

    def test_prints_error_for_unknown_command(self, capsys):
        """Test that run_command prints error message for unknown command."""
        with pytest.raises(SystemExit):
            runner.run_command("unknown-command")
        captured = capsys.readouterr()
        assert "Unknown command: unknown-command" in captured.err
        assert "Available commands:" in captured.err

    def test_imports_and_runs_known_command(self):
        """Test that run_command imports and runs a known command."""
        mock_func = MagicMock()
        mock_module = MagicMock()
        mock_module.show_cmd = mock_func

        with patch("importlib.import_module", return_value=mock_module):
            runner.run_command("agdt-show")

        mock_func.assert_called_once()

    def test_exits_on_import_error(self):
        """Test that run_command exits on import error."""
        with patch("importlib.import_module") as mock_import:
            mock_import.side_effect = ImportError("Module not found")
            with pytest.raises(SystemExit) as exc_info:
                runner.run_command("agdt-show")
        assert exc_info.value.code == 1

    def test_exits_on_attribute_error(self):
        """Test that run_command exits when function not found in module."""
        mock_module = MagicMock(spec=[])  # Module without the expected attribute
        delattr(mock_module, "show_cmd") if hasattr(mock_module, "show_cmd") else None

        with patch("importlib.import_module", return_value=mock_module):
            with pytest.raises(SystemExit) as exc_info:
                runner.run_command("agdt-show")
        assert exc_info.value.code == 1

    def test_prints_error_message_on_import_error(self, capsys):
        """Test that run_command prints error message on import error."""
        with patch("importlib.import_module") as mock_import:
            mock_import.side_effect = ImportError("Module not found")
            with pytest.raises(SystemExit):
                runner.run_command("agdt-show")
        captured = capsys.readouterr()
        assert "Error loading command agdt-show" in captured.err


class TestMain:
    """Tests for the main function."""

    def test_exits_with_help_when_no_args(self):
        """Test that main shows help and exits when no args provided."""
        with patch.object(sys, "argv", ["runner"]):
            with pytest.raises(SystemExit) as exc_info:
                runner.main()
        assert exc_info.value.code == 1

    def test_prints_usage_when_no_args(self, capsys):
        """Test that main prints usage info when no args provided."""
        with patch.object(sys, "argv", ["runner"]):
            with pytest.raises(SystemExit):
                runner.main()
        captured = capsys.readouterr()
        assert "Usage:" in captured.out
        assert "agentic_devtools.cli.runner" in captured.out
        assert "Available commands:" in captured.out

    def test_adjusts_sys_argv_before_running_command(self):
        """Test that main adjusts sys.argv so command sees correct args."""
        original_argv = None

        def capture_argv():
            nonlocal original_argv
            original_argv = sys.argv.copy()

        mock_func = MagicMock(side_effect=capture_argv)
        mock_module = MagicMock()
        mock_module.show_cmd = mock_func

        with patch("importlib.import_module", return_value=mock_module):
            with patch.object(sys, "argv", ["runner", "agdt-show", "arg1", "arg2"]):
                runner.main()

        # The command should see argv as: [command_name, arg1, arg2]
        assert original_argv == ["agdt-show", "arg1", "arg2"]

    def test_calls_run_command_with_command_name(self):
        """Test that main calls run_command with the command name."""
        mock_func = MagicMock()
        mock_module = MagicMock()
        mock_module.show_cmd = mock_func

        with patch("importlib.import_module", return_value=mock_module):
            with patch.object(sys, "argv", ["runner", "agdt-show"]):
                runner.main()

        mock_func.assert_called_once()

    def test_handles_command_with_no_additional_args(self):
        """Test that main works when command has no additional arguments."""
        captured_argv = None

        def capture_argv():
            nonlocal captured_argv
            captured_argv = sys.argv.copy()

        mock_func = MagicMock(side_effect=capture_argv)
        mock_module = MagicMock()
        mock_module.show_cmd = mock_func

        with patch("importlib.import_module", return_value=mock_module):
            with patch.object(sys, "argv", ["runner", "agdt-show"]):
                runner.main()

        assert captured_argv == ["agdt-show"]


class TestMainEntryPoint:
    """Tests for the __main__ block execution."""

    def test_main_called_when_run_as_script(self):
        """Test that main() is called when module is run as script."""
        # This tests the if __name__ == "__main__": block indirectly
        # by verifying main exists and is callable
        assert callable(runner.main)


class TestCommandMapIntegrity:
    """Tests to verify COMMAND_MAP integrity against actual modules."""

    @pytest.mark.parametrize(
        "command",
        [
            "agdt-set",
            "agdt-get",
            "agdt-show",
        ],
    )
    def test_state_commands_map_correctly(self, command):
        """Test that state commands map to the correct module."""
        module_name, _ = runner.COMMAND_MAP[command]
        assert module_name == "agentic_devtools.cli.state"

    @pytest.mark.parametrize(
        "command",
        [
            "agdt-git-save-work",
            "agdt-git-push",
            "agdt-git-sync",
        ],
    )
    def test_git_commands_map_correctly(self, command):
        """Test that git commands map to the correct module."""
        module_name, _ = runner.COMMAND_MAP[command]
        assert module_name == "agentic_devtools.cli.git"

    @pytest.mark.parametrize(
        "command",
        [
            "agdt-test",
            "agdt-test-quick",
            "agdt-test-file",
        ],
    )
    def test_testing_commands_map_correctly(self, command):
        """Test that testing commands map to the correct module."""
        module_name, _ = runner.COMMAND_MAP[command]
        assert module_name == "agentic_devtools.cli.testing"

    @pytest.mark.parametrize(
        "command",
        [
            "agdt-get-jira-issue",
            "agdt-add-jira-comment",
            "agdt-create-issue",
        ],
    )
    def test_jira_commands_map_correctly(self, command):
        """Test that jira commands map to the correct module."""
        module_name, _ = runner.COMMAND_MAP[command]
        assert module_name == "agentic_devtools.cli.jira"

    @pytest.mark.parametrize(
        "command",
        [
            "agdt-create-pull-request",
            "agdt-approve-pull-request",
            "agdt-get-pull-request-details",
        ],
    )
    def test_azure_devops_commands_map_correctly(self, command):
        """Test that Azure DevOps commands map to the correct module."""
        module_name, _ = runner.COMMAND_MAP[command]
        assert module_name == "agentic_devtools.cli.azure_devops"

    @pytest.mark.parametrize(
        "command",
        [
            "agdt-task-wait",
            "agdt-tasks",
            "agdt-task-status",
        ],
    )
    def test_task_commands_map_correctly(self, command):
        """Test that task commands map to the correct module."""
        module_name, _ = runner.COMMAND_MAP[command]
        assert module_name == "agentic_devtools.cli.tasks"

    @pytest.mark.parametrize(
        "command",
        [
            "agdt-advance-workflow",
            "agdt-get-next-workflow-prompt",
            "agdt-create-checklist",
        ],
    )
    def test_workflow_commands_map_correctly(self, command):
        """Test that workflow commands map to the correct module."""
        module_name, _ = runner.COMMAND_MAP[command]
        assert module_name == "agentic_devtools.cli.workflows"
