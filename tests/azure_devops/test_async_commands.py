"""
Tests for Azure DevOps async commands.

Tests verify that async commands spawn background tasks correctly,
calling Python functions directly via run_function_in_background.
"""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.azure_devops.async_commands import (
    add_pull_request_comment_async,
    approve_file_async,
    approve_pull_request_async,
    create_pull_request_async,
    generate_pr_summary_async,
    get_pull_request_details_async,
    get_pull_request_threads_async,
    get_run_details_async,
    mark_file_reviewed_async,
    mark_pull_request_draft_async,
    publish_pull_request_async,
    reply_to_pull_request_thread_async,
    request_changes_async,
    request_changes_with_suggestion_async,
    resolve_thread_async,
    run_e2e_tests_fabric_async,
    run_e2e_tests_synapse_async,
    run_wb_patch_async,
    submit_file_review_async,
)


@pytest.fixture
def mock_background_and_state(tmp_path):
    """Mock both background task infrastructure and state."""
    # Need to patch get_state_dir in both modules since task_state imports it directly
    with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
        with patch("agentic_devtools.task_state.get_state_dir", return_value=tmp_path):
            # Patch subprocess.Popen only in the background_tasks module, not globally
            # This prevents interference with subprocess.run usage in state.py
            with patch("agentic_devtools.background_tasks.subprocess.Popen") as mock_popen:
                mock_process = MagicMock()
                mock_process.pid = 12345
                mock_popen.return_value = mock_popen
                yield {
                    "state_dir": tmp_path,
                    "mock_popen": mock_popen,
                }


def _get_script_from_call(mock_popen):
    """Extract the Python script from the Popen call args."""
    call_args = mock_popen.call_args[0][0]  # First positional arg is the command list
    # Script is the third element: [python, -c, <script>]
    return call_args[2] if len(call_args) > 2 else ""


def _assert_function_in_script(script: str, module_path: str, function_name: str):
    """Assert that the generated script calls the correct module and function."""
    assert f"module_path = '{module_path}'" in script, f"Expected module_path='{module_path}' in script"
    assert f"function_name = '{function_name}'" in script, f"Expected function_name='{function_name}' in script"


# =============================================================================
# Helper Function Tests
# =============================================================================


class TestRequireValue:
    """Tests for _require_value helper."""

    def test_exits_when_value_missing(self, temp_state_dir, clear_state_before, capsys):
        """Should exit with error when required value is not set."""
        from agentic_devtools.cli.azure_devops.async_commands import _require_value

        with pytest.raises(SystemExit) as exc_info:
            _require_value("missing_key", "dfly-set missing_key <value>")

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "missing_key" in captured.err
        assert "required" in captured.err.lower()

    def test_returns_value_when_set(self, temp_state_dir, clear_state_before):
        """Should return the value when it is set."""
        from agentic_devtools.cli.azure_devops.async_commands import _require_value
        from agentic_devtools.state import set_value

        set_value("test_key", "test_value")

        result = _require_value("test_key", "dfly-set test_key <value>")
        assert result == "test_value"


# =============================================================================
# Pull Request Commands Tests
# =============================================================================


class TestAddPullRequestCommentAsync:
    """Tests for add_pull_request_comment_async command."""

    def test_spawns_background_task(self, mock_background_and_state, capsys):
        """Test command spawns a background task calling the correct function."""
        add_pull_request_comment_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

        script = _get_script_from_call(mock_background_and_state["mock_popen"])
        _assert_function_in_script(script, "agentic_devtools.cli.azure_devops.commands", "add_pull_request_comment")


class TestApprovePullRequestAsync:
    """Tests for approve_pull_request_async command."""

    def test_spawns_background_task(self, mock_background_and_state, capsys):
        """Test command spawns a background task calling the correct function."""
        approve_pull_request_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

        script = _get_script_from_call(mock_background_and_state["mock_popen"])
        _assert_function_in_script(script, "agentic_devtools.cli.azure_devops.commands", "approve_pull_request")


class TestCreatePullRequestAsync:
    """Tests for create_pull_request_async command."""

    def test_spawns_background_task(self, mock_background_and_state, capsys):
        """Test command spawns a background task calling the correct function."""
        # Set required state values for validation
        from agentic_devtools.state import set_value

        set_value("source_branch", "feature/test-branch")
        set_value("title", "Test PR title")

        create_pull_request_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

        script = _get_script_from_call(mock_background_and_state["mock_popen"])
        _assert_function_in_script(script, "agentic_devtools.cli.azure_devops.commands", "create_pull_request")

    def test_accepts_cli_parameters(self, mock_background_and_state, capsys):
        """Test command accepts CLI parameters that override state."""
        create_pull_request_async(
            source_branch="feature/cli-branch",
            title="CLI PR title",
            description="CLI description",
        )

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

        # Verify state was set from CLI params
        from agentic_devtools.state import get_value

        assert get_value("source_branch") == "feature/cli-branch"
        assert get_value("title") == "CLI PR title"
        assert get_value("description") == "CLI description"


class TestGetPullRequestThreadsAsync:
    """Tests for get_pull_request_threads_async command."""

    def test_spawns_background_task(self, mock_background_and_state, capsys):
        """Test command spawns a background task calling the correct function."""
        get_pull_request_threads_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

        script = _get_script_from_call(mock_background_and_state["mock_popen"])
        _assert_function_in_script(script, "agentic_devtools.cli.azure_devops.commands", "get_pull_request_threads")


class TestReplyToThreadAsync:
    """Tests for reply_to_pull_request_thread_async command."""

    def test_spawns_background_task(self, mock_background_and_state, capsys):
        """Test command spawns a background task calling the correct function."""
        reply_to_pull_request_thread_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

        script = _get_script_from_call(mock_background_and_state["mock_popen"])
        _assert_function_in_script(script, "agentic_devtools.cli.azure_devops.commands", "reply_to_pull_request_thread")


class TestResolveThreadAsync:
    """Tests for resolve_thread_async command."""

    def test_spawns_background_task(self, mock_background_and_state, capsys):
        """Test command spawns a background task calling the correct function."""
        resolve_thread_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

        script = _get_script_from_call(mock_background_and_state["mock_popen"])
        _assert_function_in_script(script, "agentic_devtools.cli.azure_devops.commands", "resolve_thread")


class TestMarkPullRequestDraftAsync:
    """Tests for mark_pull_request_draft_async command."""

    def test_spawns_background_task(self, mock_background_and_state, capsys):
        """Test command spawns a background task calling the correct function."""
        mark_pull_request_draft_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

        script = _get_script_from_call(mock_background_and_state["mock_popen"])
        _assert_function_in_script(script, "agentic_devtools.cli.azure_devops.commands", "mark_pull_request_draft")


class TestPublishPullRequestAsync:
    """Tests for publish_pull_request_async command."""

    def test_spawns_background_task(self, mock_background_and_state, capsys):
        """Test command spawns a background task calling the correct function."""
        publish_pull_request_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

        script = _get_script_from_call(mock_background_and_state["mock_popen"])
        _assert_function_in_script(script, "agentic_devtools.cli.azure_devops.commands", "publish_pull_request")


class TestGetPullRequestDetailsAsync:
    """Tests for get_pull_request_details_async command."""

    def test_spawns_background_task(self, mock_background_and_state, capsys):
        """Test command spawns a background task calling the correct function."""
        get_pull_request_details_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

        script = _get_script_from_call(mock_background_and_state["mock_popen"])
        _assert_function_in_script(
            script, "agentic_devtools.cli.azure_devops.pull_request_details_commands", "get_pull_request_details"
        )


# =============================================================================
# Pipeline Commands Tests
# =============================================================================


class TestRunE2ETestsSynapseAsync:
    """Tests for run_e2e_tests_synapse_async command."""

    def test_spawns_background_task(self, mock_background_and_state, capsys):
        """Test command spawns a background task calling the correct function."""
        run_e2e_tests_synapse_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

        script = _get_script_from_call(mock_background_and_state["mock_popen"])
        _assert_function_in_script(
            script, "agentic_devtools.cli.azure_devops.pipeline_commands", "run_e2e_tests_synapse"
        )


class TestRunE2ETestsFabricAsync:
    """Tests for run_e2e_tests_fabric_async command."""

    def test_spawns_background_task(self, mock_background_and_state, capsys):
        """Test command spawns a background task calling the correct function."""
        run_e2e_tests_fabric_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

        script = _get_script_from_call(mock_background_and_state["mock_popen"])
        _assert_function_in_script(
            script,
            "agentic_devtools.cli.azure_devops.pipeline_commands",
            "run_e2e_tests_fabric",
        )


class TestRunWbPatchAsync:
    """Tests for run_wb_patch_async command."""

    def test_spawns_background_task(self, mock_background_and_state, capsys):
        """Test command spawns a background task calling the correct function."""
        run_wb_patch_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

        script = _get_script_from_call(mock_background_and_state["mock_popen"])
        _assert_function_in_script(script, "agentic_devtools.cli.azure_devops.pipeline_commands", "run_wb_patch")


class TestGetRunDetailsAsync:
    """Tests for get_run_details_async command."""

    def test_spawns_background_task(self, mock_background_and_state, capsys):
        """Test command spawns a background task calling the correct function."""
        get_run_details_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

        script = _get_script_from_call(mock_background_and_state["mock_popen"])
        _assert_function_in_script(script, "agentic_devtools.cli.azure_devops.run_details_commands", "get_run_details")


# =============================================================================
# File Review Commands Tests
# =============================================================================


class TestApproveFileAsync:
    """Tests for approve_file_async command."""

    def test_spawns_background_task(self, mock_background_and_state, capsys):
        """Test command spawns a background task calling the correct function."""
        # Set required state values for validation
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("file_review.file_path", "src/app/component.ts")
        set_value("content", "LGTM")

        approve_file_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

        script = _get_script_from_call(mock_background_and_state["mock_popen"])
        _assert_function_in_script(script, "agentic_devtools.cli.azure_devops.file_review_commands", "approve_file")

    def test_accepts_cli_parameters(self, mock_background_and_state, capsys):
        """Test command accepts CLI parameters that override state."""
        approve_file_async(
            file_path="src/cli/test.ts",
            content="Approved via CLI",
            pull_request_id=99999,
        )

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

        # Verify state was set from CLI params
        from agentic_devtools.state import get_value

        assert get_value("file_review.file_path") == "src/cli/test.ts"
        assert get_value("content") == "Approved via CLI"
        assert get_value("pull_request_id") == 99999


class TestSubmitFileReviewAsync:
    """Tests for submit_file_review_async command."""

    def test_spawns_background_task(self, mock_background_and_state, capsys):
        """Test command spawns a background task calling the correct function."""
        submit_file_review_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

        script = _get_script_from_call(mock_background_and_state["mock_popen"])
        _assert_function_in_script(
            script, "agentic_devtools.cli.azure_devops.file_review_commands", "submit_file_review"
        )


class TestRequestChangesAsync:
    """Tests for request_changes_async command."""

    def test_spawns_background_task(self, mock_background_and_state, capsys):
        """Test command spawns a background task calling the correct function."""
        # Set required state values for validation
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("file_review.file_path", "src/app/component.ts")
        set_value("content", "Please fix this issue")
        set_value("line", 42)

        request_changes_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

        script = _get_script_from_call(mock_background_and_state["mock_popen"])
        _assert_function_in_script(script, "agentic_devtools.cli.azure_devops.file_review_commands", "request_changes")

    def test_accepts_cli_parameters(self, mock_background_and_state, capsys):
        """Test command accepts CLI parameters that override state."""
        request_changes_async(
            file_path="src/cli/test.ts",
            content="Issue via CLI",
            line=100,
            pull_request_id=99999,
        )

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

        # Verify state was set from CLI params
        from agentic_devtools.state import get_value

        assert get_value("file_review.file_path") == "src/cli/test.ts"
        assert get_value("content") == "Issue via CLI"
        assert get_value("line") == 100


class TestRequestChangesWithSuggestionAsync:
    """Tests for request_changes_with_suggestion_async command."""

    def test_spawns_background_task(self, mock_background_and_state, capsys):
        """Test command spawns a background task calling the correct function."""
        # Set required state values for validation
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("file_review.file_path", "src/app/component.ts")
        set_value("content", "```suggestion\nconst x = 1;\n```")
        set_value("line", 42)

        request_changes_with_suggestion_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

        script = _get_script_from_call(mock_background_and_state["mock_popen"])
        _assert_function_in_script(
            script, "agentic_devtools.cli.azure_devops.file_review_commands", "request_changes_with_suggestion"
        )

    def test_accepts_cli_parameters(self, mock_background_and_state, capsys):
        """Test command accepts CLI parameters that override state."""
        request_changes_with_suggestion_async(
            file_path="src/cli/test.ts",
            content="```suggestion\nconst y = 2;\n```",
            line=200,
            pull_request_id=99999,
        )

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

        # Verify state was set from CLI params
        from agentic_devtools.state import get_value

        assert get_value("file_review.file_path") == "src/cli/test.ts"
        assert get_value("line") == 200


class TestMarkFileReviewedAsync:
    """Tests for mark_file_reviewed_async command."""

    def test_spawns_background_task(self, mock_background_and_state, capsys):
        """Test command spawns a background task calling the correct function."""
        mark_file_reviewed_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

        script = _get_script_from_call(mock_background_and_state["mock_popen"])
        _assert_function_in_script(script, "agentic_devtools.cli.azure_devops.mark_reviewed", "mark_file_reviewed_cli")


# =============================================================================
# Review Workflow Commands Tests
# =============================================================================


class TestGeneratePrSummaryAsync:
    """Tests for generate_pr_summary_async command."""

    def test_spawns_background_task(self, mock_background_and_state, capsys):
        """Test command spawns a background task calling the correct function."""
        generate_pr_summary_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

        script = _get_script_from_call(mock_background_and_state["mock_popen"])
        _assert_function_in_script(
            script, "agentic_devtools.cli.azure_devops.pr_summary_commands", "generate_overarching_pr_comments_cli"
        )


# =============================================================================
# Integration Tests
# =============================================================================


class TestAzureDevOpsAsyncIntegration:
    """Integration tests for Azure DevOps async commands."""

    def test_all_commands_importable(self):
        """Test all async commands can be imported."""
        from agentic_devtools.cli.azure_devops.async_commands import (
            add_pull_request_comment_async,
            approve_file_async,
            approve_pull_request_async,
            create_pull_request_async,
            generate_pr_summary_async,
            get_pull_request_details_async,
            get_pull_request_threads_async,
            get_run_details_async,
            mark_file_reviewed_async,
            mark_pull_request_draft_async,
            publish_pull_request_async,
            reply_to_pull_request_thread_async,
            request_changes_async,
            request_changes_with_suggestion_async,
            resolve_thread_async,
            run_e2e_tests_fabric_async,
            run_e2e_tests_synapse_async,
            run_wb_patch_async,
            submit_file_review_async,
        )

        # All should be callable
        assert callable(add_pull_request_comment_async)
        assert callable(approve_pull_request_async)
        assert callable(create_pull_request_async)
        assert callable(get_pull_request_threads_async)
        assert callable(reply_to_pull_request_thread_async)
        assert callable(resolve_thread_async)
        assert callable(mark_pull_request_draft_async)
        assert callable(publish_pull_request_async)
        assert callable(get_pull_request_details_async)
        assert callable(run_e2e_tests_synapse_async)
        assert callable(run_e2e_tests_fabric_async)
        assert callable(run_wb_patch_async)
        assert callable(get_run_details_async)
        assert callable(approve_file_async)
        assert callable(submit_file_review_async)
        assert callable(request_changes_async)
        assert callable(request_changes_with_suggestion_async)
        assert callable(mark_file_reviewed_async)
        assert callable(generate_pr_summary_async)

    def test_all_commands_print_tracking_info(self, mock_background_and_state, capsys):
        """Test all commands print task tracking instructions."""
        # Set up required state for commands that validate
        from agentic_devtools.state import set_value

        set_value("source_branch", "feature/test-branch")
        set_value("title", "Test PR title")

        commands = [
            add_pull_request_comment_async,
            approve_pull_request_async,
            create_pull_request_async,
            get_pull_request_threads_async,
        ]

        for cmd in commands:
            cmd()
            captured = capsys.readouterr()
            assert "Background task started" in captured.out
            assert "task_id automatically set" in captured.out
            # Simplified output now only shows dfly-task-wait
            assert "dfly-task-wait" in captured.out

    def test_task_ids_are_unique(self, mock_background_and_state, capsys):
        """Test each spawned task gets a unique ID."""
        add_pull_request_comment_async()
        out1 = capsys.readouterr().out

        approve_pull_request_async()
        out2 = capsys.readouterr().out

        # Extract task IDs from output (new format - match the first occurrence per output)
        import re

        # Use the "Background task started (command: ..., id: ...)" pattern
        id1_match = re.search(r"Background task started \(command: [^,]+, id: ([a-f0-9-]+)\)", out1)
        id2_match = re.search(r"Background task started \(command: [^,]+, id: ([a-f0-9-]+)\)", out2)
        assert id1_match is not None, f"No task ID found in: {out1}"
        assert id2_match is not None, f"No task ID found in: {out2}"
        assert id1_match.group(1) != id2_match.group(1)


class TestAsyncCliEntryPoints:
    """Tests for CLI entry point functions with argument parsing."""

    def test_create_pull_request_async_cli_with_args(self, mock_background_and_state, capsys, monkeypatch):
        """Test create_pull_request_async_cli parses CLI arguments."""
        from agentic_devtools.cli.azure_devops.async_commands import create_pull_request_async_cli

        # Mock sys.argv with CLI arguments
        monkeypatch.setattr(
            "sys.argv",
            ["dfly-create-pull-request", "--source-branch", "feature/test", "--title", "Test PR"],
        )

        create_pull_request_async_cli()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

    def test_create_pull_request_async_cli_without_args(self, mock_background_and_state, capsys, monkeypatch):
        """Test create_pull_request_async_cli uses state when no args provided."""
        from agentic_devtools.cli.azure_devops.async_commands import create_pull_request_async_cli
        from agentic_devtools.state import set_value

        # Set state values
        set_value("source_branch", "feature/from-state")
        set_value("title", "Title from state")

        # Mock sys.argv with no arguments
        monkeypatch.setattr("sys.argv", ["dfly-create-pull-request"])

        create_pull_request_async_cli()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

    def test_approve_file_async_cli_with_args(self, mock_background_and_state, capsys, monkeypatch):
        """Test approve_file_async_cli parses CLI arguments."""
        from agentic_devtools.cli.azure_devops.async_commands import approve_file_async_cli
        from agentic_devtools.state import set_value

        # Set required state
        set_value("pull_request_id", "12345")

        monkeypatch.setattr(
            "sys.argv",
            ["dfly-approve-file", "--file-path", "path/to/file.py", "--content", "LGTM"],
        )

        approve_file_async_cli()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

    def test_approve_file_async_cli_without_args(self, mock_background_and_state, capsys, monkeypatch):
        """Test approve_file_async_cli uses state when no args provided."""
        from agentic_devtools.cli.azure_devops.async_commands import approve_file_async_cli
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "12345")
        set_value("file_review.file_path", "path/from/state.py")
        set_value("content", "LGTM from state")
        monkeypatch.setattr("sys.argv", ["dfly-approve-file"])

        approve_file_async_cli()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

    def test_request_changes_async_cli_with_args(self, mock_background_and_state, capsys, monkeypatch):
        """Test request_changes_async_cli parses CLI arguments."""
        from agentic_devtools.cli.azure_devops.async_commands import request_changes_async_cli
        from agentic_devtools.state import set_value

        # Set required pull_request_id
        set_value("pull_request_id", "12345")

        monkeypatch.setattr(
            "sys.argv",
            [
                "dfly-request-changes",
                "--file-path",
                "path/to/file.py",
                "--content",
                "Need changes here",
                "--line",
                "42",
            ],
        )

        request_changes_async_cli()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

    def test_request_changes_async_cli_without_args(self, mock_background_and_state, capsys, monkeypatch):
        """Test request_changes_async_cli uses state when no args provided."""
        from agentic_devtools.cli.azure_devops.async_commands import request_changes_async_cli
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "12345")
        set_value("file_review.file_path", "path/from/state.py")
        set_value("content", "Comment from state")
        set_value("line", "42")
        monkeypatch.setattr("sys.argv", ["dfly-request-changes"])

        request_changes_async_cli()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

    def test_request_changes_with_suggestion_async_cli_with_args(self, mock_background_and_state, capsys, monkeypatch):
        """Test request_changes_with_suggestion_async_cli parses CLI arguments."""
        from agentic_devtools.cli.azure_devops.async_commands import request_changes_with_suggestion_async_cli
        from agentic_devtools.state import set_value

        # Set required pull_request_id
        set_value("pull_request_id", "12345")

        monkeypatch.setattr(
            "sys.argv",
            [
                "dfly-request-changes-with-suggestion",
                "--file-path",
                "file.py",
                "--content",
                "Suggested change",
                "--line",
                "10",
            ],
        )

        request_changes_with_suggestion_async_cli()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

    def test_request_changes_with_suggestion_async_cli_without_args(
        self, mock_background_and_state, capsys, monkeypatch
    ):
        """Test request_changes_with_suggestion_async_cli uses state when no args."""
        from agentic_devtools.cli.azure_devops.async_commands import request_changes_with_suggestion_async_cli
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "12345")
        set_value("file_review.file_path", "file.py")
        set_value("content", "Suggested change from state")
        set_value("line", "10")
        monkeypatch.setattr("sys.argv", ["dfly-request-changes-with-suggestion"])

        request_changes_with_suggestion_async_cli()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out


# =============================================================================
# Cross-Context Lookup Commands Tests
# =============================================================================


class TestLookupJiraIssueFromPrAsync:
    """Tests for lookup_jira_issue_from_pr_async function."""

    def test_extracts_issue_key_from_pr(self, mock_background_and_state, capsys):
        """Test extracting issue key using find_jira_issue_from_pr helper."""
        from agentic_devtools.cli.azure_devops.async_commands import lookup_jira_issue_from_pr_async
        from agentic_devtools.state import get_value

        # Patch the unified helper function
        with patch("agentic_devtools.cli.azure_devops.helpers.find_jira_issue_from_pr") as mock_find:
            mock_find.return_value = "DFLY-1234"

            lookup_jira_issue_from_pr_async(12345)

            mock_find.assert_called_once_with(12345)
            assert get_value("jira.issue_key") == "DFLY-1234"

        captured = capsys.readouterr()
        assert "Found Jira issue DFLY-1234" in captured.out

    def test_does_not_overwrite_existing_jira_key(self, mock_background_and_state, capsys):
        """Test that existing jira.issue_key is not overwritten."""
        from agentic_devtools.cli.azure_devops.async_commands import lookup_jira_issue_from_pr_async
        from agentic_devtools.state import get_value, set_value

        # Set existing key
        set_value("jira.issue_key", "DFLY-EXISTING")

        with patch("agentic_devtools.cli.azure_devops.helpers.find_jira_issue_from_pr") as mock_find:
            mock_find.return_value = "DFLY-1234"

            lookup_jira_issue_from_pr_async(12345)

            # Should NOT overwrite
            assert get_value("jira.issue_key") == "DFLY-EXISTING"

    def test_no_issue_key_found(self, mock_background_and_state, capsys):
        """Test handling when no issue key found."""
        from agentic_devtools.cli.azure_devops.async_commands import lookup_jira_issue_from_pr_async
        from agentic_devtools.state import get_value

        with patch("agentic_devtools.cli.azure_devops.helpers.find_jira_issue_from_pr") as mock_find:
            mock_find.return_value = None

            lookup_jira_issue_from_pr_async(12345)

            assert get_value("jira.issue_key") is None

        captured = capsys.readouterr()
        assert "No Jira issue key found" in captured.out

    def test_handles_exception_gracefully(self, mock_background_and_state, capsys):
        """Test that exceptions don't propagate."""
        from agentic_devtools.cli.azure_devops.async_commands import lookup_jira_issue_from_pr_async

        with patch("agentic_devtools.cli.azure_devops.helpers.find_jira_issue_from_pr") as mock_find:
            mock_find.side_effect = Exception("Network error")

            # Should not raise
            lookup_jira_issue_from_pr_async(12345)

        captured = capsys.readouterr()
        assert "Could not look up Jira issue from PR" in captured.out


class TestLookupPrFromJiraIssueAsync:
    """Tests for lookup_pr_from_jira_issue_async function."""

    def test_finds_pr_by_issue_key(self, mock_background_and_state, capsys):
        """Test finding PR by issue key using unified helper."""
        from agentic_devtools.cli.azure_devops.async_commands import lookup_pr_from_jira_issue_async
        from agentic_devtools.state import get_value

        # Patch the unified helper function
        with patch("agentic_devtools.cli.azure_devops.helpers.find_pr_from_jira_issue") as mock_find:
            mock_find.return_value = 99999

            lookup_pr_from_jira_issue_async("DFLY-1234")

            mock_find.assert_called_once_with("DFLY-1234")
            assert get_value("pull_request_id") == "99999"

        captured = capsys.readouterr()
        assert "Found PR #99999" in captured.out

    def test_does_not_overwrite_existing_pr_id(self, mock_background_and_state, capsys):
        """Test that existing pull_request_id is not overwritten."""
        from agentic_devtools.cli.azure_devops.async_commands import lookup_pr_from_jira_issue_async
        from agentic_devtools.state import get_value, set_value

        # Set existing PR ID
        set_value("pull_request_id", 11111)

        with patch("agentic_devtools.cli.azure_devops.helpers.find_pr_from_jira_issue") as mock_find:
            mock_find.return_value = 99999

            lookup_pr_from_jira_issue_async("DFLY-1234")

            # Should NOT overwrite
            assert get_value("pull_request_id") == 11111

    def test_no_pr_found(self, mock_background_and_state, capsys):
        """Test handling when no PR found."""
        from agentic_devtools.cli.azure_devops.async_commands import lookup_pr_from_jira_issue_async
        from agentic_devtools.state import get_value

        with patch("agentic_devtools.cli.azure_devops.helpers.find_pr_from_jira_issue") as mock_find:
            mock_find.return_value = None

            lookup_pr_from_jira_issue_async("DFLY-1234")

            assert get_value("pull_request_id") is None

        captured = capsys.readouterr()
        assert "No active PR found" in captured.out

    def test_handles_exception_gracefully(self, mock_background_and_state, capsys):
        """Test that exceptions don't propagate."""
        from agentic_devtools.cli.azure_devops.async_commands import lookup_pr_from_jira_issue_async

        with patch("agentic_devtools.cli.azure_devops.helpers.find_pr_from_jira_issue") as mock_find:
            mock_find.side_effect = Exception("Network error")

            # Should not raise
            lookup_pr_from_jira_issue_async("DFLY-1234")

        captured = capsys.readouterr()
        assert "Could not look up PR from Jira issue" in captured.out
