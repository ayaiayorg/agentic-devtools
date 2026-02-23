"""Tests for AdvancePullRequestReviewWorkflow."""

from unittest.mock import patch

import pytest

from agentic_devtools import state
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
    state_file = temp_state_dir / "agdt-state.json"
    if state_file.exists():
        state_file.unlink()
    yield


@pytest.fixture
def mock_workflow_state_clearing():
    """Mock clear_state_for_workflow_initiation to be a no-op.

    This is needed because workflow initiation commands clear all state at the start,
    but tests set up state before calling the command. Without this mock, the test's
    state setup would be wiped immediately.
    """
    with patch("agentic_devtools.cli.workflows.commands.clear_state_for_workflow_initiation"):
        yield


class TestAdvancePullRequestReviewWorkflow:
    """Tests for advance_pull_request_review_workflow function."""

    def test_advance_no_active_workflow(self, temp_state_dir, clear_state_before, capsys):
        """Test advance fails when workflow is not active."""
        with pytest.raises(SystemExit) as exc_info:
            commands.advance_pull_request_review_workflow()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "pull-request-review workflow is not active" in captured.err

    def test_advance_no_workflow_state(self, temp_state_dir, clear_state_before, capsys):
        """Test advance fails when get_workflow_state returns None."""
        with patch("agentic_devtools.state.is_workflow_active", return_value=True):
            with patch("agentic_devtools.state.get_workflow_state", return_value=None):
                with pytest.raises(SystemExit) as exc_info:
                    commands.advance_pull_request_review_workflow()
                assert exc_info.value.code == 1
                captured = capsys.readouterr()
                assert "Could not get workflow state" in captured.err

    def test_advance_no_pull_request_id(self, temp_state_dir, clear_state_before, capsys):
        """Test advance fails when no pull_request_id in context or state."""
        state.set_workflow_state(
            name="pull-request-review",
            status="in-progress",
            step="initiate",
            context={},
        )

        with pytest.raises(SystemExit) as exc_info:
            commands.advance_pull_request_review_workflow()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "No pull_request_id found" in captured.err

    def test_advance_invalid_pull_request_id(self, temp_state_dir, clear_state_before, capsys):
        """Test advance fails when pull_request_id is invalid."""
        state.set_workflow_state(
            name="pull-request-review",
            status="in-progress",
            step="initiate",
            context={"pull_request_id": "not-a-number"},
        )

        with pytest.raises(SystemExit) as exc_info:
            commands.advance_pull_request_review_workflow()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Invalid pull_request_id" in captured.err

    def test_advance_auto_detects_summary_when_all_files_complete(
        self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys
    ):
        """Test advance auto-detects summary step when all files are complete."""
        state.set_workflow_state(
            name="pull-request-review",
            status="in-progress",
            step="file-review",
            context={"pull_request_id": "123"},
        )

        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands.get_queue_status",
            return_value={
                "all_complete": True,
                "completed_count": 5,
                "pending_count": 0,
                "total_count": 5,
                "current_file": None,
                "prompt_file_path": None,
            },
        ):
            workflow_dir = temp_prompts_dir / "pull-request-review"
            workflow_dir.mkdir()
            template_file = workflow_dir / "default-summary-prompt.md"
            template_file.write_text("Summary for PR #{{pull_request_id}}", encoding="utf-8")

            commands.advance_pull_request_review_workflow()

        workflow = state.get_workflow_state()
        assert workflow["step"] == "summary"

    def test_advance_stays_on_file_review_when_files_pending(
        self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys
    ):
        """Test advance stays on file-review when files are still pending."""
        state.set_workflow_state(
            name="pull-request-review",
            status="in-progress",
            step="file-review",
            context={"pull_request_id": "123"},
        )

        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands.get_queue_status",
            return_value={
                "all_complete": False,
                "completed_count": 3,
                "pending_count": 2,
                "total_count": 5,
                "current_file": "src/file.py",
                "prompt_file_path": "/tmp/prompt.md",
            },
        ):
            workflow_dir = temp_prompts_dir / "pull-request-review"
            workflow_dir.mkdir()
            template_file = workflow_dir / "default-file-review-prompt.md"
            template_file.write_text("File review for PR #{{pull_request_id}}", encoding="utf-8")

            commands.advance_pull_request_review_workflow()

        workflow = state.get_workflow_state()
        assert workflow["step"] == "file-review"

    def test_advance_from_initiate_to_file_review(
        self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys
    ):
        """Test advance from initiate step goes to file-review."""
        state.set_workflow_state(
            name="pull-request-review",
            status="in-progress",
            step="initiate",
            context={"pull_request_id": "123"},
        )

        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands.get_queue_status",
            return_value={
                "all_complete": False,
                "completed_count": 0,
                "pending_count": 5,
                "total_count": 5,
                "current_file": "src/file.py",
                "prompt_file_path": "/tmp/prompt.md",
            },
        ):
            workflow_dir = temp_prompts_dir / "pull-request-review"
            workflow_dir.mkdir()
            template_file = workflow_dir / "default-file-review-prompt.md"
            template_file.write_text("File review for PR #{{pull_request_id}}", encoding="utf-8")

            commands.advance_pull_request_review_workflow()

        workflow = state.get_workflow_state()
        assert workflow["step"] == "file-review"
