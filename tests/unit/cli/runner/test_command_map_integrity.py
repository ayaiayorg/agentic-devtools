"""
Tests for cli/runner.py module.

This module tests the command runner that maps agdt-* commands to their
entry point functions.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest
from agentic_devtools.cli import runner


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

    @pytest.mark.parametrize(
        "command",
        [
            "agdt-release-pypi",
            "agdt-azure-context-use",
            "agdt-azure-context-status",
            "agdt-network-status",
            "agdt-vpn-run",
        ],
    )
    def test_newly_added_commands_exist(self, command):
        """Test that commands previously missing from COMMAND_MAP are present."""
        assert command in runner.COMMAND_MAP, (
            f"Expected command '{command}' not in COMMAND_MAP"
        )
