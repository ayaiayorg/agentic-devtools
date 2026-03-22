"""Tests for _format_auto_setup_success_message."""

from agentic_devtools.cli.workflows.commands import _format_auto_setup_success_message


class TestFormatAutoSetupSuccessMessage:
    """Tests for _format_auto_setup_success_message helper function."""

    def test_includes_workflow_name(self):
        """Test that the message includes the workflow name."""
        result = _format_auto_setup_success_message("work-on-jira-issue", "PROJECT-1234")
        assert "work-on-jira-issue" in result

    def test_includes_issue_key(self):
        """Test that the message includes the issue key."""
        result = _format_auto_setup_success_message("work-on-jira-issue", "PROJECT-1234")
        assert "PROJECT-1234" in result

    def test_includes_auto_session_text(self):
        """Test that the message describes automatic Copilot session launch."""
        result = _format_auto_setup_success_message("pull-request-review", "PR12345")
        assert "Copilot session will start automatically" in result

    def test_includes_fallback_instruction(self):
        """Test that the message includes the agdt-task-log fallback instruction."""
        result = _format_auto_setup_success_message("create-jira-issue", "PROJECT-5678")
        assert "agdt-task-log" in result

    def test_returns_string(self):
        """Test that the function returns a string."""
        result = _format_auto_setup_success_message("update-jira-issue", "PROJECT-999")
        assert isinstance(result, str)

    def test_different_workflows_produce_different_messages(self):
        """Test that different workflow names produce different messages."""
        msg1 = _format_auto_setup_success_message("work-on-jira-issue", "PROJECT-1")
        msg2 = _format_auto_setup_success_message("create-jira-issue", "PROJECT-1")
        assert msg1 != msg2

    def test_different_issue_keys_produce_different_messages(self):
        """Test that different issue keys produce different messages."""
        msg1 = _format_auto_setup_success_message("work-on-jira-issue", "PROJECT-1111")
        msg2 = _format_auto_setup_success_message("work-on-jira-issue", "PROJECT-2222")
        assert msg1 != msg2
        assert "PROJECT-1111" in msg1
        assert "PROJECT-2222" in msg2

    def test_includes_visual_separator(self):
        """Test that the message includes visual separators."""
        result = _format_auto_setup_success_message("work-on-jira-issue", "PROJECT-1234")
        assert "=" * 80 in result
