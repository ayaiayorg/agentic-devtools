"""Tests for InitiateWorkflow."""

import re
from subprocess import CompletedProcess
from unittest.mock import patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli.workflows import base
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


class TestInitiateWorkflow:
    """Tests for initiate_workflow function."""

    def test_initiate_workflow_success(
        self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys
    ):
        """Test successful workflow initiation."""
        # Setup template in workflow subfolder
        workflow_dir = temp_prompts_dir / "pull-request-review"
        workflow_dir.mkdir()
        template = "Working on PR #{{pull_request_id}}"
        template_file = workflow_dir / "default-initiate-prompt.md"
        template_file.write_text(template, encoding="utf-8")

        # Setup state
        state.set_value("pull_request_id", "123")

        # Initiate workflow
        base.initiate_workflow(
            workflow_name="pull-request-review",
            required_state_keys=["pull_request_id"],
            optional_state_keys=[],
        )

        # Verify workflow state
        workflow = state.get_workflow_state()
        assert workflow is not None
        assert workflow["active"] == "pull-request-review"
        assert workflow["status"] == "initiated"
        assert workflow["step"] == "initiate"

        # Verify output
        captured = capsys.readouterr()
        assert "Working on PR #123" in captured.out

    def test_initiate_workflow_missing_required_state(self, temp_state_dir, temp_prompts_dir, clear_state_before):
        """Test workflow initiation fails with missing required state."""
        # Setup template in workflow subfolder
        workflow_dir = temp_prompts_dir / "pull-request-review"
        workflow_dir.mkdir()
        template = "Template {{pull_request_id}}"
        template_file = workflow_dir / "default-initiate-prompt.md"
        template_file.write_text(template, encoding="utf-8")

        # Don't set required state
        with pytest.raises(SystemExit) as exc_info:
            base.initiate_workflow(
                workflow_name="pull-request-review",
                required_state_keys=["pull_request_id"],
                optional_state_keys=[],
            )
        assert exc_info.value.code == 1

    def test_initiate_workflow_with_optional_state(
        self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys
    ):
        """Test workflow initiation with optional state."""
        # Setup template with optional variable in workflow subfolder
        workflow_dir = temp_prompts_dir / "pull-request-review"
        workflow_dir.mkdir()
        template = "PR #{{pull_request_id}}"
        template_file = workflow_dir / "default-initiate-prompt.md"
        template_file.write_text(template, encoding="utf-8")

        # Setup required state only
        state.set_value("pull_request_id", "123")

        # Initiate workflow - should succeed even without optional state
        base.initiate_workflow(
            workflow_name="pull-request-review",
            required_state_keys=["pull_request_id"],
            optional_state_keys=["jira.issue_key"],
        )

        captured = capsys.readouterr()
        assert "PR #123" in captured.out

    def test_run_id_generated_on_initiation(
        self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys
    ):
        """initiate_workflow generates a 12-char hex run_id."""
        workflow_dir = temp_prompts_dir / "pull-request-review"
        workflow_dir.mkdir()
        template_file = workflow_dir / "default-initiate-prompt.md"
        template_file.write_text("PR #{{pull_request_id}}", encoding="utf-8")

        state.set_value("pull_request_id", "123")

        with patch(
            "agentic_devtools.cli.git.agdt_branch._run_plumbing",
            return_value=CompletedProcess(args=[], returncode=0, stdout="feature/test\n", stderr=""),
        ):
            base.initiate_workflow(
                workflow_name="pull-request-review",
                required_state_keys=["pull_request_id"],
                optional_state_keys=[],
            )

        run_id = state.get_value("agdt_run_id")
        assert run_id is not None
        assert len(run_id) == 12
        assert re.fullmatch(r"[0-9a-f]{12}", run_id)

    def test_current_branch_stored_on_initiation(
        self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys
    ):
        """initiate_workflow stores versionControl.currentBranch from git."""
        workflow_dir = temp_prompts_dir / "pull-request-review"
        workflow_dir.mkdir()
        template_file = workflow_dir / "default-initiate-prompt.md"
        template_file.write_text("PR #{{pull_request_id}}", encoding="utf-8")

        state.set_value("pull_request_id", "123")

        with patch(
            "agentic_devtools.cli.git.agdt_branch._run_plumbing",
            return_value=CompletedProcess(args=[], returncode=0, stdout="feature/PROJECT-1234\n", stderr=""),
        ):
            base.initiate_workflow(
                workflow_name="pull-request-review",
                required_state_keys=["pull_request_id"],
                optional_state_keys=[],
            )

        branch = state.get_value("versionControl.currentBranch")
        assert branch == "feature/PROJECT-1234"

    def test_current_branch_not_stored_on_detached_head(
        self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys
    ):
        """initiate_workflow skips versionControl.currentBranch when detached HEAD."""
        workflow_dir = temp_prompts_dir / "pull-request-review"
        workflow_dir.mkdir()
        template_file = workflow_dir / "default-initiate-prompt.md"
        template_file.write_text("PR #{{pull_request_id}}", encoding="utf-8")

        state.set_value("pull_request_id", "123")

        with patch(
            "agentic_devtools.cli.git.agdt_branch._run_plumbing",
            return_value=CompletedProcess(args=[], returncode=0, stdout="HEAD\n", stderr=""),
        ):
            base.initiate_workflow(
                workflow_name="pull-request-review",
                required_state_keys=["pull_request_id"],
                optional_state_keys=[],
            )

        branch = state.get_value("versionControl.currentBranch")
        assert branch is None

    def test_run_id_is_unique_across_initiations(
        self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys
    ):
        """Two initiate_workflow calls generate different run_ids."""
        workflow_dir = temp_prompts_dir / "pull-request-review"
        workflow_dir.mkdir()
        template_file = workflow_dir / "default-initiate-prompt.md"
        template_file.write_text("PR #{{pull_request_id}}", encoding="utf-8")

        state.set_value("pull_request_id", "123")

        with patch(
            "agentic_devtools.cli.git.agdt_branch._run_plumbing",
            return_value=CompletedProcess(args=[], returncode=0, stdout="main\n", stderr=""),
        ):
            base.initiate_workflow(
                workflow_name="pull-request-review",
                required_state_keys=["pull_request_id"],
                optional_state_keys=[],
            )

        run_id_1 = state.get_value("agdt_run_id")

        with patch(
            "agentic_devtools.cli.git.agdt_branch._run_plumbing",
            return_value=CompletedProcess(args=[], returncode=0, stdout="main\n", stderr=""),
        ):
            base.initiate_workflow(
                workflow_name="pull-request-review",
                required_state_keys=["pull_request_id"],
                optional_state_keys=[],
            )

        run_id_2 = state.get_value("agdt_run_id")
        assert run_id_1 != run_id_2

    def test_initiate_workflow_continues_when_bootstrap_fails(
        self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, caplog
    ):
        """Bootstrap initialization failures are logged and do not block workflow initiation."""
        workflow_dir = temp_prompts_dir / "pull-request-review"
        workflow_dir.mkdir()
        template_file = workflow_dir / "default-initiate-prompt.md"
        template_file.write_text("PR #{{pull_request_id}}", encoding="utf-8")

        state.set_value("pull_request_id", "123")

        with patch("agentic_devtools.cli.workflows.base.set_bootstrap_state", side_effect=OSError("boom")):
            with patch(
                "agentic_devtools.cli.git.agdt_branch._run_plumbing",
                return_value=CompletedProcess(args=[], returncode=0, stdout="feature/test\n", stderr=""),
            ):
                base.initiate_workflow(
                    workflow_name="pull-request-review",
                    required_state_keys=["pull_request_id"],
                    optional_state_keys=[],
                )

        workflow = state.get_workflow_state()
        assert workflow is not None
        assert workflow["active"] == "pull-request-review"
        assert "Failed to initialize bootstrap state" in caplog.text

    def test_initiate_workflow_continues_when_branch_detection_raises(
        self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before
    ):
        """Branch detection is best-effort and should not block workflow initiation."""
        workflow_dir = temp_prompts_dir / "pull-request-review"
        workflow_dir.mkdir()
        template_file = workflow_dir / "default-initiate-prompt.md"
        template_file.write_text("PR #{{pull_request_id}}", encoding="utf-8")

        state.set_value("pull_request_id", "123")

        with patch("agentic_devtools.cli.git.agdt_branch._run_plumbing", side_effect=RuntimeError("git error")):
            base.initiate_workflow(
                workflow_name="pull-request-review",
                required_state_keys=["pull_request_id"],
                optional_state_keys=[],
            )

        workflow = state.get_workflow_state()
        assert workflow is not None
        assert workflow["active"] == "pull-request-review"
        assert state.get_value("versionControl.currentBranch") is None

    def test_initiate_workflow_skips_bootstrap_when_env_override_set(
        self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys
    ):
        """When AGENTIC_DEVTOOLS_STATE_DIR is set, bootstrap init is skipped."""
        workflow_dir = temp_prompts_dir / "pull-request-review"
        workflow_dir.mkdir()
        template_file = workflow_dir / "default-initiate-prompt.md"
        template_file.write_text("PR #{{pull_request_id}}", encoding="utf-8")

        state.set_value("pull_request_id", "123")

        with patch.dict("os.environ", {"AGENTIC_DEVTOOLS_STATE_DIR": "/tmp/override"}):
            with patch("agentic_devtools.cli.workflows.base.set_bootstrap_state") as mock_bootstrap:
                base.initiate_workflow(
                    workflow_name="pull-request-review",
                    required_state_keys=["pull_request_id"],
                    optional_state_keys=[],
                )
                mock_bootstrap.assert_not_called()

        workflow = state.get_workflow_state()
        assert workflow is not None
        assert workflow["active"] == "pull-request-review"

    def test_initiate_workflow_no_required_state_keys(
        self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys
    ):
        """Workflow initiation succeeds when required_state_keys is None."""
        workflow_dir = temp_prompts_dir / "simple-workflow"
        workflow_dir.mkdir()
        template_file = workflow_dir / "default-initiate-prompt.md"
        template_file.write_text("Simple prompt", encoding="utf-8")

        base.initiate_workflow(
            workflow_name="simple-workflow",
            required_state_keys=None,
            optional_state_keys=None,
        )

        workflow = state.get_workflow_state()
        assert workflow is not None
        assert workflow["active"] == "simple-workflow"

        captured = capsys.readouterr()
        assert "Simple prompt" in captured.out

    def test_initiate_workflow_with_additional_variables(
        self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys
    ):
        """Additional variables are merged into template variables."""
        workflow_dir = temp_prompts_dir / "pull-request-review"
        workflow_dir.mkdir()
        template_file = workflow_dir / "default-initiate-prompt.md"
        template_file.write_text("PR #{{pull_request_id}} by {{author}}", encoding="utf-8")

        state.set_value("pull_request_id", "123")

        base.initiate_workflow(
            workflow_name="pull-request-review",
            required_state_keys=["pull_request_id"],
            optional_state_keys=[],
            additional_variables={"author": "tester"},
        )

        captured = capsys.readouterr()
        assert "by tester" in captured.out

    def test_initiate_workflow_with_explicit_context(
        self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys
    ):
        """When context is explicitly provided, it is used as-is."""
        workflow_dir = temp_prompts_dir / "pull-request-review"
        workflow_dir.mkdir()
        template_file = workflow_dir / "default-initiate-prompt.md"
        template_file.write_text("PR #{{pull_request_id}}", encoding="utf-8")

        state.set_value("pull_request_id", "123")

        custom_context = {"custom_key": "custom_value"}
        base.initiate_workflow(
            workflow_name="pull-request-review",
            required_state_keys=["pull_request_id"],
            optional_state_keys=[],
            context=custom_context,
        )

        workflow = state.get_workflow_state()
        assert workflow is not None
        assert workflow["context"] == custom_context
