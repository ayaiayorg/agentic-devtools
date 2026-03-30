"""Tests for AdvancePullRequestReviewWorkflow."""

from unittest.mock import MagicMock, patch

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

    def test_advance_auto_detects_decision_when_all_files_complete(
        self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys
    ):
        """Test advance auto-detects decision step when all files are complete."""
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
            template_file = workflow_dir / "default-decision-prompt.md"
            template_file.write_text(
                "Decision for PR #{{pull_request_id}}\n"
                "Files: {{completed_count}} Approvals: {{approval_count}} Changes: {{changes_count}}",
                encoding="utf-8",
            )

            commands.advance_pull_request_review_workflow()

        workflow = state.get_workflow_state()
        assert workflow["step"] == "decision"

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

    def test_advance_to_decision_computes_approval_and_changes_counts(
        self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys
    ):
        """Test decision step receives approval_count and changes_count from review-state."""
        state.set_workflow_state(
            name="pull-request-review",
            status="in-progress",
            step="file-review",
            context={"pull_request_id": "123"},
        )

        mock_file_approved = MagicMock()
        mock_file_approved.status = "approved"
        mock_file_needswork = MagicMock()
        mock_file_needswork.status = "needs-work"
        mock_review_state = MagicMock()
        mock_review_state.files = {
            "/src/a.py": mock_file_approved,
            "/src/b.py": mock_file_approved,
            "/src/c.py": mock_file_needswork,
        }

        with (
            patch(
                "agentic_devtools.cli.azure_devops.file_review_commands.get_queue_status",
                return_value={
                    "all_complete": True,
                    "completed_count": 3,
                    "pending_count": 0,
                    "total_count": 3,
                    "current_file": None,
                    "prompt_file_path": None,
                },
            ),
            patch(
                "agentic_devtools.cli.azure_devops.review_state.load_review_state",
                return_value=mock_review_state,
            ),
        ):
            workflow_dir = temp_prompts_dir / "pull-request-review"
            workflow_dir.mkdir()
            template_file = workflow_dir / "default-decision-prompt.md"
            template_file.write_text(
                "Approvals: {{approval_count}}, Changes: {{changes_count}}",
                encoding="utf-8",
            )

            commands.advance_pull_request_review_workflow()

        captured = capsys.readouterr()
        assert "Approvals: 2" in captured.out
        assert "Changes: 1" in captured.out

    def test_advance_from_initiate_to_pull_request_overview(
        self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys
    ):
        """Test advance from initiate step goes to pull-request-overview."""
        state.set_workflow_state(
            name="pull-request-review",
            status="in-progress",
            step="initiate",
            context={
                "pull_request_id": "123",
                "pr_url": "https://dev.azure.com/org/proj/_git/repo/pullrequest/123",
                "source_code_platform": "AzureDevOps",
            },
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
            template_file = workflow_dir / "default-pull-request-overview-prompt.md"
            template_file.write_text(
                "Overview for PR #{{pull_request_id}} at {{pr_url}}",
                encoding="utf-8",
            )

            commands.advance_pull_request_review_workflow()

        workflow = state.get_workflow_state()
        assert workflow["step"] == "pull-request-overview"

    def test_advance_from_pull_request_overview_to_file_review(
        self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys
    ):
        """Test advance from pull-request-overview step goes to file-review."""
        state.set_workflow_state(
            name="pull-request-review",
            status="in-progress",
            step="pull-request-overview",
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

    def test_advance_rejects_invalid_step(self, temp_state_dir, clear_state_before, capsys):
        """Test advance rejects removed/unknown steps like 'summary'."""
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
                "completed_count": 0,
                "pending_count": 5,
                "total_count": 5,
                "current_file": None,
                "prompt_file_path": None,
            },
        ):
            with pytest.raises(SystemExit) as exc_info:
                commands.advance_pull_request_review_workflow(step="summary")
            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "Unknown step 'summary'" in captured.err
            assert "completion" in captured.err
            assert "decision" in captured.err
            assert "file-review" in captured.err
            assert "pull-request-overview" in captured.err

    def test_advance_to_completion_triggers_cascade(
        self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys
    ):
        """Test advance to completion step triggers status cascade and saves review state."""
        state.set_workflow_state(
            name="pull-request-review",
            status="in-progress",
            step="decision",
            context={"pull_request_id": "123"},
        )

        mock_file_approved = MagicMock()
        mock_file_approved.status = "approved"
        mock_review_state = MagicMock()
        mock_review_state.files = {"/src/a.py": mock_file_approved}
        mock_review_state.repoId = "repo-guid"
        mock_review_state.overallSummary = MagicMock()
        mock_review_state.overallSummary.status = "approved"

        mock_patch_ops = [MagicMock()]

        with (
            patch(
                "agentic_devtools.cli.azure_devops.file_review_commands.get_queue_status",
                return_value={
                    "all_complete": True,
                    "completed_count": 1,
                    "pending_count": 0,
                    "total_count": 1,
                    "current_file": None,
                    "prompt_file_path": None,
                },
            ),
            patch(
                "agentic_devtools.cli.azure_devops.review_state.load_review_state",
                return_value=mock_review_state,
            ) as mock_load,
            patch(
                "agentic_devtools.cli.azure_devops.status_cascade.cascade_overall_summary_update",
                return_value=mock_patch_ops,
            ) as mock_cascade,
            patch(
                "agentic_devtools.cli.azure_devops.status_cascade.execute_cascade",
            ) as mock_execute,
            patch(
                "agentic_devtools.cli.azure_devops.review_state.save_review_state",
            ) as mock_save,
            patch(
                "agentic_devtools.cli.azure_devops.auth.get_pat",
                return_value="fake-pat",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.auth.get_auth_headers",
                return_value={"Authorization": "Basic fake"},
            ),
            patch(
                "agentic_devtools.cli.azure_devops.helpers.require_requests",
                return_value=MagicMock(),
            ),
            patch(
                "agentic_devtools.cli.azure_devops.config.AzureDevOpsConfig.from_state",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.review_scaffold.build_pr_base_url",
                return_value="https://dev.azure.com/org/proj/_git/repo/pullrequest/123",
            ),
        ):
            workflow_dir = temp_prompts_dir / "pull-request-review"
            workflow_dir.mkdir()
            template_file = workflow_dir / "default-completion-prompt.md"
            template_file.write_text(
                "Complete! Decision: {{decision}}",
                encoding="utf-8",
            )

            commands.advance_pull_request_review_workflow(step="completion")

        mock_load.assert_called_with(123)
        mock_cascade.assert_called_once()
        mock_execute.assert_called_once()
        mock_save.assert_called_once_with(mock_review_state)

        workflow = state.get_workflow_state()
        assert workflow["step"] == "completion"
        assert workflow["status"] == "completed"

    def test_advance_to_completion_sets_decision_variable(
        self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys
    ):
        """Test decision variable is derived from overall status and rendered in prompt."""
        state.set_workflow_state(
            name="pull-request-review",
            status="in-progress",
            step="decision",
            context={"pull_request_id": "123"},
        )

        mock_file = MagicMock()
        mock_file.status = "approved"
        mock_review_state = MagicMock()
        mock_review_state.files = {"/src/a.py": mock_file}
        mock_review_state.repoId = "repo-guid"
        mock_review_state.overallSummary = MagicMock()
        mock_review_state.overallSummary.status = "approved"

        with (
            patch(
                "agentic_devtools.cli.azure_devops.file_review_commands.get_queue_status",
                return_value={
                    "all_complete": True,
                    "completed_count": 1,
                    "pending_count": 0,
                    "total_count": 1,
                    "current_file": None,
                    "prompt_file_path": None,
                },
            ),
            patch(
                "agentic_devtools.cli.azure_devops.review_state.load_review_state",
                return_value=mock_review_state,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.status_cascade.cascade_overall_summary_update",
                return_value=[],
            ),
            patch(
                "agentic_devtools.cli.azure_devops.status_cascade.execute_cascade",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.review_state.save_review_state",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.auth.get_pat",
                return_value="fake-pat",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.auth.get_auth_headers",
                return_value={"Authorization": "Basic fake"},
            ),
            patch(
                "agentic_devtools.cli.azure_devops.helpers.require_requests",
                return_value=MagicMock(),
            ),
            patch(
                "agentic_devtools.cli.azure_devops.config.AzureDevOpsConfig.from_state",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.review_scaffold.build_pr_base_url",
                return_value="https://dev.azure.com/org/proj/_git/repo/pullrequest/123",
            ),
        ):
            workflow_dir = temp_prompts_dir / "pull-request-review"
            workflow_dir.mkdir()
            template_file = workflow_dir / "default-completion-prompt.md"
            template_file.write_text(
                "Decision: {{decision}}",
                encoding="utf-8",
            )

            commands.advance_pull_request_review_workflow(step="completion")

        captured = capsys.readouterr()
        assert "✅ Approved" in captured.out

    def test_advance_to_completion_skips_cascade_when_review_state_missing(
        self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys
    ):
        """Test workflow still completes when review state file is not found."""
        state.set_workflow_state(
            name="pull-request-review",
            status="in-progress",
            step="decision",
            context={"pull_request_id": "123"},
        )

        with (
            patch(
                "agentic_devtools.cli.azure_devops.file_review_commands.get_queue_status",
                return_value={
                    "all_complete": True,
                    "completed_count": 1,
                    "pending_count": 0,
                    "total_count": 1,
                    "current_file": None,
                    "prompt_file_path": None,
                },
            ),
            patch(
                "agentic_devtools.cli.azure_devops.review_state.load_review_state",
                side_effect=FileNotFoundError("review-state.json not found"),
            ),
        ):
            workflow_dir = temp_prompts_dir / "pull-request-review"
            workflow_dir.mkdir()
            template_file = workflow_dir / "default-completion-prompt.md"
            template_file.write_text(
                "Complete! Decision: {{decision}}",
                encoding="utf-8",
            )

            commands.advance_pull_request_review_workflow(step="completion")

        captured = capsys.readouterr()
        assert "Review state not found" in captured.err
        assert "⚠️ Unavailable" in captured.out

        workflow = state.get_workflow_state()
        assert workflow["step"] == "completion"
        assert workflow["status"] == "completed"

    def test_advance_to_completion_continues_on_cascade_error(
        self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys
    ):
        """Test workflow completes even when cascade execution fails, and state is saved."""
        state.set_workflow_state(
            name="pull-request-review",
            status="in-progress",
            step="decision",
            context={"pull_request_id": "123"},
        )

        mock_file = MagicMock()
        mock_file.status = "needs-work"
        mock_review_state = MagicMock()
        mock_review_state.files = {"/src/a.py": mock_file}
        mock_review_state.repoId = "repo-guid"
        mock_review_state.overallSummary = MagicMock()
        mock_review_state.overallSummary.status = "needs-work"

        with (
            patch(
                "agentic_devtools.cli.azure_devops.file_review_commands.get_queue_status",
                return_value={
                    "all_complete": True,
                    "completed_count": 1,
                    "pending_count": 0,
                    "total_count": 1,
                    "current_file": None,
                    "prompt_file_path": None,
                },
            ),
            patch(
                "agentic_devtools.cli.azure_devops.review_state.load_review_state",
                return_value=mock_review_state,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.status_cascade.cascade_overall_summary_update",
                return_value=[MagicMock()],
            ),
            patch(
                "agentic_devtools.cli.azure_devops.status_cascade.execute_cascade",
                side_effect=RuntimeError("API call failed"),
            ),
            patch(
                "agentic_devtools.cli.azure_devops.review_state.save_review_state",
            ) as mock_save,
            patch(
                "agentic_devtools.cli.azure_devops.auth.get_pat",
                return_value="fake-pat",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.auth.get_auth_headers",
                return_value={"Authorization": "Basic fake"},
            ),
            patch(
                "agentic_devtools.cli.azure_devops.helpers.require_requests",
                return_value=MagicMock(),
            ),
            patch(
                "agentic_devtools.cli.azure_devops.config.AzureDevOpsConfig.from_state",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.review_scaffold.build_pr_base_url",
                return_value="https://dev.azure.com/org/proj/_git/repo/pullrequest/123",
            ),
        ):
            workflow_dir = temp_prompts_dir / "pull-request-review"
            workflow_dir.mkdir()
            template_file = workflow_dir / "default-completion-prompt.md"
            template_file.write_text(
                "Complete! Decision: {{decision}}",
                encoding="utf-8",
            )

            commands.advance_pull_request_review_workflow(step="completion")

        captured = capsys.readouterr()
        assert "Failed to update PR summary" in captured.err

        # Decision should still be derived even though cascade failed
        assert "📝 Needs Work" in captured.out

        # save_review_state should still be called (finally block)
        mock_save.assert_called_once_with(mock_review_state)

        workflow = state.get_workflow_state()
        assert workflow["step"] == "completion"
        assert workflow["status"] == "completed"

    def test_advance_to_completion_handles_malformed_state_gracefully(
        self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys
    ):
        """Test workflow completes even when cascade raises ValueError/KeyError from bad state."""
        state.set_workflow_state(
            name="pull-request-review",
            status="in-progress",
            step="decision",
            context={"pull_request_id": "123"},
        )

        with (
            patch(
                "agentic_devtools.cli.azure_devops.file_review_commands.get_queue_status",
                return_value={
                    "all_complete": True,
                    "completed_count": 1,
                    "pending_count": 0,
                    "total_count": 1,
                    "current_file": None,
                    "prompt_file_path": None,
                },
            ),
            patch(
                "agentic_devtools.cli.azure_devops.review_state.load_review_state",
                side_effect=ValueError("malformed review state"),
            ),
        ):
            workflow_dir = temp_prompts_dir / "pull-request-review"
            workflow_dir.mkdir()
            template_file = workflow_dir / "default-completion-prompt.md"
            template_file.write_text(
                "Complete! Decision: {{decision}}",
                encoding="utf-8",
            )

            commands.advance_pull_request_review_workflow(step="completion")

        captured = capsys.readouterr()
        assert "Could not update PR summary" in captured.err
        assert "⚠️ Unavailable" in captured.out

        workflow = state.get_workflow_state()
        assert workflow["step"] == "completion"
        assert workflow["status"] == "completed"
