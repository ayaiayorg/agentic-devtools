"""Tests for ExecuteRetrieveStep."""

from unittest.mock import patch

import pytest

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
    """Clear state before each test.

    Note: We only remove the state file, not the entire temp folder,
    to avoid deleting directories created by other fixtures (like temp_prompts_dir).
    """
    state_file = temp_state_dir / "state.json"
    if state_file.exists():
        state_file.unlink()
    yield


@pytest.fixture
def mock_workflow_state_clearing():
    """Mock clear_state_for_workflow_initiation to be a no-op.

    Workflow initiation commands reset workflow tracking keys (workflow,
    agdt_run_id) at the start.  This fixture prevents that reset, which
    is useful when tests pre-set workflow state before calling the command.
    """
    with patch("agentic_devtools.cli.workflows.commands.clear_state_for_workflow_initiation"):
        yield


class TestExecuteRetrieveStep:
    """Tests for _execute_retrieve_step function."""

    def test_get_issue_failure(self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys):
        """Test handling of get_issue failure (SystemExit)."""
        workflow_dir = temp_prompts_dir / "work-on-jira-issue"
        workflow_dir.mkdir()
        template_file = workflow_dir / "default-planning-prompt.md"
        template_file.write_text("Planning for {{issue_key}}", encoding="utf-8")

        with patch("agentic_devtools.cli.jira.get_commands.get_issue") as mock_get_issue:
            mock_get_issue.side_effect = SystemExit(1)

            commands._execute_retrieve_step("DFLY-1234", "feature/DFLY-1234/test")

        captured = capsys.readouterr()
        assert "Warning: Failed to fetch issue DFLY-1234" in captured.err

    def test_get_issue_exception(self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys):
        """Test handling of general exception when calling get_issue."""
        workflow_dir = temp_prompts_dir / "work-on-jira-issue"
        workflow_dir.mkdir()
        template_file = workflow_dir / "default-planning-prompt.md"
        template_file.write_text("Planning for {{issue_key}}", encoding="utf-8")

        with patch("agentic_devtools.cli.jira.get_commands.get_issue") as mock_get_issue:
            mock_get_issue.side_effect = Exception("Connection failed")

            commands._execute_retrieve_step("DFLY-1234", "feature/DFLY-1234/test")

        captured = capsys.readouterr()
        assert "Warning: Could not fetch Jira issue" in captured.err

    def test_formats_recent_comments(
        self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys
    ):
        """Test that recent comments are formatted correctly.

        Patches commands.get_state_dir so the module-level binding uses temp_state_dir
        and finds the pre-populated issue file (covering lines 591-594 and 608-613).
        """
        import json

        workflow_dir = temp_prompts_dir / "work-on-jira-issue"
        workflow_dir.mkdir()
        template_file = workflow_dir / "default-planning-prompt.md"
        template_file.write_text("Planning for {{issue_key}}", encoding="utf-8")

        issue_data = {
            "fields": {
                "summary": "Test issue",
                "issuetype": {"name": "Task"},
                "labels": [],
                "description": "Test description",
                "comment": {
                    "comments": [
                        {"author": {"displayName": "User 1"}, "body": "First comment"},
                        {"author": {"displayName": "User 2"}, "body": "Second comment"},
                    ]
                },
            }
        }
        issue_file = temp_state_dir / "temp-get-issue-details-response.json"
        issue_file.write_text(json.dumps(issue_data), encoding="utf-8")

        with patch("agentic_devtools.cli.jira.get_commands.get_issue") as mock_get_issue:
            with patch("agentic_devtools.cli.workflows.commands.get_state_dir", return_value=temp_state_dir):
                mock_get_issue.return_value = None
                commands._execute_retrieve_step("DFLY-1234", "feature/DFLY-1234/test")

        captured = capsys.readouterr()
        assert "Issue DFLY-1234 retrieved successfully" in captured.out