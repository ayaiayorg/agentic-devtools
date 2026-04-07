"""Tests for _print_agent_instructions_block helper."""

from unittest.mock import patch

from agentic_devtools.cli.workflows.worktree_setup import (
    _print_agent_instructions_block,
)


class TestPrintAgentInstructionsBlock:
    """Tests for the _print_agent_instructions_block helper function."""

    @patch("agentic_devtools.cli.workflows.worktree_setup.get_ai_agent_continuation_prompt")
    def test_success_header_when_autostart_injected(self, mock_ai_prompt, capsys):
        """When autostart_injected is True, header should say (FALLBACK)."""
        mock_ai_prompt.return_value = "AI Agent prompt"

        _print_agent_instructions_block(
            autostart_injected=True,
            issue_key="PROJECT-1234",
            workflow_name="work-on-jira-issue",
        )

        captured = capsys.readouterr()
        assert "AI AGENT INSTRUCTIONS (FALLBACK)" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.get_ai_agent_continuation_prompt")
    def test_success_message_when_autostart_injected(self, mock_ai_prompt, capsys):
        """When autostart_injected is True, message should say auto-start task was injected."""
        mock_ai_prompt.return_value = "AI Agent prompt"

        _print_agent_instructions_block(
            autostart_injected=True,
            issue_key="PROJECT-1234",
            workflow_name="work-on-jira-issue",
        )

        captured = capsys.readouterr()
        assert "auto-start task was injected" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.get_ai_agent_continuation_prompt")
    def test_failure_header_when_autostart_not_injected(self, mock_ai_prompt, capsys):
        """When autostart_injected is False, header should say (MANUAL START REQUIRED)."""
        mock_ai_prompt.return_value = "AI Agent prompt"

        _print_agent_instructions_block(
            autostart_injected=False,
            issue_key="PROJECT-1234",
            workflow_name="work-on-jira-issue",
        )

        captured = capsys.readouterr()
        assert "AI AGENT INSTRUCTIONS (MANUAL START REQUIRED)" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.get_ai_agent_continuation_prompt")
    def test_failure_message_when_autostart_not_injected(self, mock_ai_prompt, capsys):
        """When autostart_injected is False, message should say injection was not successful."""
        mock_ai_prompt.return_value = "AI Agent prompt"

        _print_agent_instructions_block(
            autostart_injected=False,
            issue_key="PROJECT-1234",
            workflow_name="work-on-jira-issue",
        )

        captured = capsys.readouterr()
        assert "Auto-start injection was not successful" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.get_ai_agent_continuation_prompt")
    def test_no_success_message_when_autostart_not_injected(self, mock_ai_prompt, capsys):
        """When autostart_injected is False, should NOT contain the success message."""
        mock_ai_prompt.return_value = "AI Agent prompt"

        _print_agent_instructions_block(
            autostart_injected=False,
            issue_key="PROJECT-1234",
            workflow_name="work-on-jira-issue",
        )

        captured = capsys.readouterr()
        assert "auto-start task was injected" not in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.get_ai_agent_continuation_prompt")
    def test_prompt_markers_always_present_when_injected(self, mock_ai_prompt, capsys):
        """BEGIN/END PROMPT markers should always be present when autostart_injected is True."""
        mock_ai_prompt.return_value = "AI Agent prompt"

        _print_agent_instructions_block(
            autostart_injected=True,
            issue_key="PROJECT-1234",
            workflow_name="work-on-jira-issue",
        )

        captured = capsys.readouterr()
        assert "--- BEGIN PROMPT FOR USER TO COPY ---" in captured.out
        assert "--- END PROMPT FOR USER TO COPY ---" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.get_ai_agent_continuation_prompt")
    def test_prompt_markers_always_present_when_not_injected(self, mock_ai_prompt, capsys):
        """BEGIN/END PROMPT markers should always be present when autostart_injected is False."""
        mock_ai_prompt.return_value = "AI Agent prompt"

        _print_agent_instructions_block(
            autostart_injected=False,
            issue_key="PROJECT-1234",
            workflow_name="work-on-jira-issue",
        )

        captured = capsys.readouterr()
        assert "--- BEGIN PROMPT FOR USER TO COPY ---" in captured.out
        assert "--- END PROMPT FOR USER TO COPY ---" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.get_ai_agent_continuation_prompt")
    def test_ai_prompt_content_included(self, mock_ai_prompt, capsys):
        """The AI agent continuation prompt text should be included in output."""
        mock_ai_prompt.return_value = "Run agdt-initiate-work-on-jira-issue-workflow --issue-key PROJECT-1234"

        _print_agent_instructions_block(
            autostart_injected=True,
            issue_key="PROJECT-1234",
            workflow_name="work-on-jira-issue",
        )

        captured = capsys.readouterr()
        assert "Run agdt-initiate-work-on-jira-issue-workflow --issue-key PROJECT-1234" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.get_ai_agent_continuation_prompt")
    def test_passes_all_params_to_ai_prompt(self, mock_ai_prompt, capsys):
        """All parameters should be forwarded to get_ai_agent_continuation_prompt."""
        mock_ai_prompt.return_value = "prompt"

        _print_agent_instructions_block(
            autostart_injected=True,
            issue_key="PROJECT-1234",
            workflow_name="create-jira-issue",
            user_request="Create a feature",
            additional_params={"parent_key": "PROJECT-1000"},
        )

        mock_ai_prompt.assert_called_once_with(
            "PROJECT-1234",
            "create-jira-issue",
            "Create a feature",
            {"parent_key": "PROJECT-1000"},
        )
