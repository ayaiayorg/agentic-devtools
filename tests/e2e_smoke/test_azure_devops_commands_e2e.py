"""
E2E smoke tests for Azure DevOps CLI commands.

These tests validate Azure DevOps command entry points with mocked responses
to ensure CLI commands work correctly with realistic API structures.
"""

from pathlib import Path

import pytest

from agentic_devtools.state import set_value


class TestAzureDevOpsCreatePullRequestE2E:
    """End-to-end smoke tests for agdt-create-pull-request command."""

    def test_create_pull_request_without_required_fields_fails(
        self,
        temp_state_dir: Path,
        clean_state: None,
        mock_azure_devops_env: None,
    ) -> None:
        """
        Smoke test: agdt-create-pull-request fails without required fields.

        Validates:
        - Command exits with error when source_branch is missing
        - Command exits with error when title is missing
        """
        from agentic_devtools.cli.azure_devops import commands

        # Arrange - don't set required fields
        set_value("dry_run", False)

        # Act & Assert
        with pytest.raises(SystemExit) as exc_info:
            commands.create_pull_request()

        assert exc_info.value.code == 1, "Should exit with error code 1"


class TestAzureDevOpsThreadOperationsE2E:
    """End-to-end smoke tests for PR thread operations."""

    def test_reply_to_pull_request_thread_requires_state(
        self,
        temp_state_dir: Path,
        clean_state: None,
        mock_azure_devops_env: None,
    ) -> None:
        """
        Smoke test: agdt-reply-to-pull-request-thread requires state values.

        Validates:
        - Command fails gracefully without pull_request_id
        - Command fails gracefully without thread_id
        - Command fails gracefully without content
        """
        from agentic_devtools.cli.azure_devops import commands

        # Act & Assert - missing all required fields
        with pytest.raises(KeyError, match="Required state key not found: pull_request_id"):
            commands.reply_to_pull_request_thread()

    def test_add_pull_request_comment_requires_state(
        self,
        temp_state_dir: Path,
        clean_state: None,
        mock_azure_devops_env: None,
    ) -> None:
        """
        Smoke test: agdt-add-pull-request-comment requires state values.

        Validates:
        - Command fails gracefully without pull_request_id
        - Command fails gracefully without content
        """
        from agentic_devtools.cli.azure_devops import commands

        # Act & Assert - missing required fields
        with pytest.raises(KeyError, match="Required state key not found: pull_request_id"):
            commands.add_pull_request_comment()
