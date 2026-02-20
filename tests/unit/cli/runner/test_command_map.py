"""
Tests for cli/runner.py module.

This module tests the command runner that maps agdt-* commands to their
entry point functions.
"""

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
            assert cmd.startswith("agdt-"), f"Command '{cmd}' doesn't start with 'agdt-'"

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
            assert cmd in runner.COMMAND_MAP, f"Expected command '{cmd}' not in COMMAND_MAP"

    def test_azure_cli_commands_exist(self):
        """Test that Azure CLI commands are in the map."""
        azure_commands = [
            "agdt-query-app-insights",
            "agdt-query-fabric-dap-errors",
            "agdt-query-fabric-dap-provisioning",
            "agdt-query-fabric-dap-timeline",
        ]
        for cmd in azure_commands:
            assert cmd in runner.COMMAND_MAP, f"Expected Azure command '{cmd}' not in COMMAND_MAP"

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
