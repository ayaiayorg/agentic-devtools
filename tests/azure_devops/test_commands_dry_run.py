"""
Tests for Azure DevOps CLI commands (dry-run mode).
"""

import pytest

from agentic_devtools import state
from agentic_devtools.cli import azure_devops


class TestReplyToPullRequestThread:
    """Tests for reply_to_pull_request_thread command."""

    def test_dry_run_output(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run output shows correct information."""
        state.set_pull_request_id(12345)
        state.set_thread_id(67890)
        state.set_value("content", "Test reply")
        state.set_dry_run(True)

        azure_devops.reply_to_pull_request_thread()

        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "12345" in captured.out
        assert "67890" in captured.out
        assert "Test reply" in captured.out

    def test_dry_run_with_resolve(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run shows resolve intent."""
        state.set_pull_request_id(12345)
        state.set_thread_id(67890)
        state.set_value("content", "Test reply")
        state.set_value("resolve_thread", True)
        state.set_dry_run(True)

        azure_devops.reply_to_pull_request_thread()

        captured = capsys.readouterr()
        assert "resolve" in captured.out.lower()

    def test_missing_pull_request_id(self, temp_state_dir, clear_state_before):
        """Test raises error when pull request ID is missing."""
        state.set_thread_id(67890)
        state.set_value("content", "Test reply")
        with pytest.raises(KeyError, match="pull_request_id"):
            azure_devops.reply_to_pull_request_thread()

    def test_missing_thread_id(self, temp_state_dir, clear_state_before):
        """Test raises error when thread ID is missing."""
        state.set_pull_request_id(12345)
        state.set_value("content", "Test reply")
        with pytest.raises(KeyError, match="thread_id"):
            azure_devops.reply_to_pull_request_thread()

    def test_missing_content(self, temp_state_dir, clear_state_before):
        """Test exits when content is missing."""
        state.set_pull_request_id(12345)
        state.set_thread_id(67890)
        with pytest.raises(SystemExit):
            azure_devops.reply_to_pull_request_thread()

    def test_multiline_content(self, temp_state_dir, clear_state_before, capsys):
        """Test handles multiline content."""
        state.set_pull_request_id(12345)
        state.set_thread_id(67890)
        state.set_value("content", "Line 1\nLine 2\nLine 3")
        state.set_dry_run(True)

        azure_devops.reply_to_pull_request_thread()

        captured = capsys.readouterr()
        assert "Line 1" in captured.out
        assert "Line 2" in captured.out

    def test_special_characters_in_content(self, temp_state_dir, clear_state_before, capsys):
        """Test handles special characters."""
        state.set_pull_request_id(12345)
        state.set_thread_id(67890)
        state.set_value("content", "Test with \"quotes\" and 'apostrophes' and $Special$ chars!")
        state.set_dry_run(True)

        azure_devops.reply_to_pull_request_thread()

        captured = capsys.readouterr()
        assert "quotes" in captured.out


class TestAddPullRequestComment:
    """Tests for add_pull_request_comment command."""

    def test_dry_run_basic(self, temp_state_dir, clear_state_before, capsys):
        """Test basic dry run output."""
        state.set_pull_request_id(12345)
        state.set_value("content", "Test comment")
        state.set_dry_run(True)

        azure_devops.add_pull_request_comment()

        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "12345" in captured.out
        assert "Test comment" in captured.out

    def test_dry_run_with_file_context(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run with file context."""
        state.set_pull_request_id(12345)
        state.set_value("content", "Comment on file")
        state.set_value("path", "src/main.py")
        state.set_value("line", 42)
        state.set_dry_run(True)

        azure_devops.add_pull_request_comment()

        captured = capsys.readouterr()
        assert "src/main.py" in captured.out
        assert "42" in captured.out

    def test_dry_run_with_end_line(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run with line range."""
        state.set_pull_request_id(12345)
        state.set_value("content", "Multi-line comment")
        state.set_value("path", "src/main.py")
        state.set_value("line", 10)
        state.set_value("end_line", 20)
        state.set_dry_run(True)

        azure_devops.add_pull_request_comment()

        captured = capsys.readouterr()
        assert "10" in captured.out
        assert "20" in captured.out

    def test_missing_pull_request_id(self, temp_state_dir, clear_state_before):
        """Test raises error when pull request ID is missing."""
        state.set_value("content", "Test comment")
        with pytest.raises(KeyError, match="pull_request_id"):
            azure_devops.add_pull_request_comment()

    def test_missing_content(self, temp_state_dir, clear_state_before):
        """Test exits when content is missing."""
        state.set_pull_request_id(12345)
        with pytest.raises(SystemExit):
            azure_devops.add_pull_request_comment()

    def test_approval_mode_dry_run(self, temp_state_dir, clear_state_before, capsys):
        """Test approval mode shows sentinel note."""
        state.set_pull_request_id(12345)
        state.set_value("content", "LGTM!")
        state.set_value("is_pull_request_approval", True)
        state.set_dry_run(True)

        azure_devops.add_pull_request_comment()

        captured = capsys.readouterr()
        assert "approval" in captured.out.lower() or "sentinel" in captured.out.lower()

    def test_leave_thread_active_dry_run(self, temp_state_dir, clear_state_before, capsys):
        """Test leave_thread_active mode shows in dry run."""
        state.set_pull_request_id(12345)
        state.set_value("content", "Keep this active")
        state.set_value("leave_thread_active", True)
        state.set_dry_run(True)

        azure_devops.add_pull_request_comment()

        captured = capsys.readouterr()
        # Should NOT mention resolving since leave_thread_active is True
        assert "Would also resolve" not in captured.out

    def test_default_resolves_thread_dry_run(self, temp_state_dir, clear_state_before, capsys):
        """Test default behavior shows thread will be resolved."""
        state.set_pull_request_id(12345)
        state.set_value("content", "Will resolve")
        # leave_thread_active defaults to False
        state.set_dry_run(True)

        azure_devops.add_pull_request_comment()

        captured = capsys.readouterr()
        assert "resolve" in captured.out.lower()


class TestCreatePullRequest:
    """Tests for create_pull_request command."""

    def test_dry_run_basic(self, temp_state_dir, clear_state_before, capsys):
        """Test basic dry run output."""
        state.set_value("source_branch", "feature/test")
        state.set_value("title", "Test PR")
        state.set_dry_run(True)

        azure_devops.create_pull_request()

        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "feature/test" in captured.out
        assert "Test PR" in captured.out

    def test_dry_run_with_target_branch(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run shows target branch."""
        state.set_value("source_branch", "feature/test")
        state.set_value("title", "Test PR")
        state.set_value("target_branch", "develop")
        state.set_dry_run(True)

        azure_devops.create_pull_request()

        captured = capsys.readouterr()
        assert "develop" in captured.out

    def test_dry_run_draft_mode_default(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run shows draft mode is True by default."""
        state.set_value("source_branch", "feature/test")
        state.set_value("title", "Test PR")
        state.set_dry_run(True)

        azure_devops.create_pull_request()

        captured = capsys.readouterr()
        assert "Draft Mode: True" in captured.out

    def test_dry_run_draft_mode_false(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run shows draft mode is False when set."""
        state.set_value("source_branch", "feature/test")
        state.set_value("title", "Test PR")
        state.set_value("draft", False)
        state.set_dry_run(True)

        azure_devops.create_pull_request()

        captured = capsys.readouterr()
        assert "Draft Mode: False" in captured.out

    def test_dry_run_draft_mode_bool_true(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run with draft=True boolean."""
        state.set_value("source_branch", "feature/test")
        state.set_value("title", "Test PR")
        state.set_value("draft", True)
        state.set_dry_run(True)

        azure_devops.create_pull_request()

        captured = capsys.readouterr()
        assert "Draft Mode: True" in captured.out

    def test_dry_run_draft_mode_string_true(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run with draft='true' string."""
        state.set_value("source_branch", "feature/test")
        state.set_value("title", "Test PR")
        state.set_value("draft", "true")
        state.set_dry_run(True)

        azure_devops.create_pull_request()

        captured = capsys.readouterr()
        assert "Draft Mode: True" in captured.out

    def test_dry_run_draft_mode_string_no(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run with draft='no' string."""
        state.set_value("source_branch", "feature/test")
        state.set_value("title", "Test PR")
        state.set_value("draft", "no")
        state.set_dry_run(True)

        azure_devops.create_pull_request()

        captured = capsys.readouterr()
        assert "Draft Mode: False" in captured.out

    def test_dry_run_draft_mode_string_0(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run with draft='0' string."""
        state.set_value("source_branch", "feature/test")
        state.set_value("title", "Test PR")
        state.set_value("draft", "0")
        state.set_dry_run(True)

        azure_devops.create_pull_request()

        captured = capsys.readouterr()
        assert "Draft Mode: False" in captured.out

    def test_dry_run_converts_title(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run converts Markdown title."""
        state.set_value("source_branch", "feature/test")
        state.set_value(
            "title",
            "feature([DFLY-1234](https://jira.swica.ch/browse/DFLY-1234)): test",
        )
        state.set_dry_run(True)

        azure_devops.create_pull_request()

        captured = capsys.readouterr()
        # Title should have Markdown links stripped
        assert "Title: feature(DFLY-1234): test" in captured.out

    def test_dry_run_with_description(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run shows description when provided."""
        state.set_value("source_branch", "feature/test")
        state.set_value("title", "Test PR")
        state.set_value("description", "This is a test PR description")
        state.set_dry_run(True)

        azure_devops.create_pull_request()

        captured = capsys.readouterr()
        assert "Description: This is a test PR description" in captured.out

    def test_missing_source_branch(self, temp_state_dir, clear_state_before):
        """Test exits when source branch is missing."""
        state.set_value("title", "Test PR")
        with pytest.raises(SystemExit):
            azure_devops.create_pull_request()

    def test_missing_title(self, temp_state_dir, clear_state_before):
        """Test exits when title is missing."""
        state.set_value("source_branch", "feature/test")
        with pytest.raises(SystemExit):
            azure_devops.create_pull_request()

    def test_missing_description_ok(self, temp_state_dir, clear_state_before, capsys):
        """Test missing description is OK."""
        state.set_value("source_branch", "feature/test")
        state.set_value("title", "Test PR")
        state.set_dry_run(True)

        azure_devops.create_pull_request()

        captured = capsys.readouterr()
        assert "Description:" not in captured.out  # No description line when empty


class TestResolveThread:
    """Tests for resolve_thread command."""

    def test_dry_run(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run output."""
        state.set_pull_request_id(12345)
        state.set_thread_id(67890)
        state.set_dry_run(True)

        azure_devops.resolve_thread()

        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "67890" in captured.out
        assert "12345" in captured.out

    def test_missing_pull_request_id(self, temp_state_dir, clear_state_before):
        """Test raises error when pull request ID is missing."""
        state.set_thread_id(67890)
        with pytest.raises(KeyError, match="pull_request_id"):
            azure_devops.resolve_thread()

    def test_missing_thread_id(self, temp_state_dir, clear_state_before):
        """Test raises error when thread ID is missing."""
        state.set_pull_request_id(12345)
        with pytest.raises(KeyError, match="thread_id"):
            azure_devops.resolve_thread()


class TestGetPullRequestThreads:
    """Tests for get_pull_request_threads command."""

    def test_dry_run(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run output."""
        state.set_pull_request_id(12345)
        state.set_dry_run(True)

        azure_devops.get_pull_request_threads()

        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "12345" in captured.out

    def test_missing_pull_request_id(self, temp_state_dir, clear_state_before):
        """Test raises error when pull request ID is missing."""
        with pytest.raises(KeyError, match="pull_request_id"):
            azure_devops.get_pull_request_threads()


class TestApprovePullRequest:
    """Tests for approve_pull_request command."""

    def test_dry_run(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run output."""
        state.set_pull_request_id(12345)
        state.set_value("content", "LGTM!")
        state.set_dry_run(True)

        azure_devops.approve_pull_request()

        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out

    def test_missing_pull_request_id(self, temp_state_dir, clear_state_before):
        """Test raises error when pull request ID is missing."""
        state.set_value("content", "LGTM!")
        with pytest.raises(KeyError, match="pull_request_id"):
            azure_devops.approve_pull_request()


class TestMarkPullRequestDraft:
    """Tests for mark_pull_request_draft command."""

    def test_dry_run(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run output."""
        state.set_pull_request_id(12345)
        state.set_dry_run(True)

        azure_devops.mark_pull_request_draft()

        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "12345" in captured.out
        assert "draft" in captured.out.lower()

    def test_dry_run_shows_org_project(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run shows organization and project."""
        state.set_pull_request_id(12345)
        state.set_dry_run(True)

        azure_devops.mark_pull_request_draft()

        captured = capsys.readouterr()
        assert "Org/Project:" in captured.out

    def test_missing_pull_request_id(self, temp_state_dir, clear_state_before):
        """Test raises error when pull request ID is missing."""
        state.set_dry_run(True)
        with pytest.raises(KeyError, match="pull_request_id"):
            azure_devops.mark_pull_request_draft()


class TestPublishPullRequest:
    """Tests for publish_pull_request command."""

    def test_dry_run(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run output."""
        state.set_pull_request_id(12345)
        state.set_dry_run(True)

        azure_devops.publish_pull_request()

        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "12345" in captured.out

    def test_dry_run_shows_auto_complete_will_be_enabled(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run shows auto-complete will be enabled by default."""
        state.set_pull_request_id(12345)
        state.set_dry_run(True)

        azure_devops.publish_pull_request()

        captured = capsys.readouterr()
        assert "Auto-complete: Will be enabled" in captured.out

    def test_dry_run_shows_auto_complete_skipped(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run shows auto-complete skipped when skip_auto_complete is true."""
        state.set_pull_request_id(12345)
        state.set_value("skip_auto_complete", True)
        state.set_dry_run(True)

        azure_devops.publish_pull_request()

        captured = capsys.readouterr()
        assert "Auto-complete: Skipped" in captured.out

    def test_dry_run_skip_auto_complete_string_true(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run with skip_auto_complete='true' string."""
        state.set_pull_request_id(12345)
        state.set_value("skip_auto_complete", "true")
        state.set_dry_run(True)

        azure_devops.publish_pull_request()

        captured = capsys.readouterr()
        assert "Auto-complete: Skipped" in captured.out

    def test_dry_run_skip_auto_complete_string_yes(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run with skip_auto_complete='yes' string."""
        state.set_pull_request_id(12345)
        state.set_value("skip_auto_complete", "yes")
        state.set_dry_run(True)

        azure_devops.publish_pull_request()

        captured = capsys.readouterr()
        assert "Auto-complete: Skipped" in captured.out

    def test_dry_run_skip_auto_complete_string_1(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run with skip_auto_complete='1' string."""
        state.set_pull_request_id(12345)
        state.set_value("skip_auto_complete", "1")
        state.set_dry_run(True)

        azure_devops.publish_pull_request()

        captured = capsys.readouterr()
        assert "Auto-complete: Skipped" in captured.out

    def test_dry_run_shows_org_project(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run shows organization and project."""
        state.set_pull_request_id(12345)
        state.set_dry_run(True)

        azure_devops.publish_pull_request()

        captured = capsys.readouterr()
        assert "Org/Project:" in captured.out

    def test_missing_pull_request_id(self, temp_state_dir, clear_state_before):
        """Test raises error when pull request ID is missing."""
        state.set_dry_run(True)
        with pytest.raises(KeyError, match="pull_request_id"):
            azure_devops.publish_pull_request()


class TestRunE2eTestsSynapse:
    """Tests for run_e2e_tests_synapse command."""

    def test_dry_run_output(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run output shows correct information."""
        state.set_value("branch", "feature/test-branch")
        state.set_value("e2e.stage", "DEV")
        state.set_dry_run(True)

        azure_devops.run_e2e_tests_synapse()

        captured = capsys.readouterr()
        assert "DRY-RUN" in captured.out
        assert "mgmt-e2e-tests-synapse" in captured.out
        assert "feature/test-branch" in captured.out
        assert "DEV" in captured.out

    def test_dry_run_default_stage(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run uses DEV as default stage."""
        state.set_value("branch", "feature/test-branch")
        state.set_dry_run(True)

        azure_devops.run_e2e_tests_synapse()

        captured = capsys.readouterr()
        assert "DEV" in captured.out

    def test_dry_run_int_stage(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run with INT stage."""
        state.set_value("branch", "feature/test-branch")
        state.set_value("e2e.stage", "INT")
        state.set_dry_run(True)

        azure_devops.run_e2e_tests_synapse()

        captured = capsys.readouterr()
        assert "INT" in captured.out

    def test_dry_run_shows_org_project(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run shows organization and project."""
        state.set_value("branch", "feature/test-branch")
        state.set_dry_run(True)

        azure_devops.run_e2e_tests_synapse()

        captured = capsys.readouterr()
        assert "Org" in captured.out
        assert "Project" in captured.out

    def test_missing_branch(self, temp_state_dir, clear_state_before):
        """Test exits when branch is missing."""
        state.set_dry_run(True)
        with pytest.raises(SystemExit):
            azure_devops.run_e2e_tests_synapse()

    def test_invalid_stage(self, temp_state_dir, clear_state_before):
        """Test exits when stage is invalid."""
        state.set_value("branch", "feature/test-branch")
        state.set_value("e2e.stage", "PROD")
        state.set_dry_run(True)
        with pytest.raises(SystemExit):
            azure_devops.run_e2e_tests_synapse()


class TestRunE2eTestsFabric:
    """Tests for run_e2e_tests_fabric command."""

    def test_dry_run_output(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run output shows correct information."""
        state.set_value("branch", "feature/test-branch")
        state.set_dry_run(True)

        azure_devops.run_e2e_tests_fabric()

        captured = capsys.readouterr()
        assert "DRY-RUN" in captured.out
        assert "mgmt-e2e-tests-fabric" in captured.out
        assert "feature/test-branch" in captured.out
        # Fabric tests always run in DEV (no stage parameter)

    def test_dry_run_shows_org_project(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run shows organization and project."""
        state.set_value("branch", "feature/test-branch")
        state.set_dry_run(True)

        azure_devops.run_e2e_tests_fabric()

        captured = capsys.readouterr()
        assert "Org" in captured.out
        assert "Project" in captured.out

    def test_missing_branch(self, temp_state_dir, clear_state_before):
        """Test exits when branch is missing."""
        state.set_dry_run(True)
        with pytest.raises(SystemExit):
            azure_devops.run_e2e_tests_fabric()


class TestRunWbPatch:
    """Tests for run_wb_patch command."""

    def test_dry_run_output(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run output shows correct information."""
        state.set_value("branch", "feature/test-branch")
        state.set_value("wb_patch.workbench", "STND")
        state.set_dry_run(True)

        azure_devops.run_wb_patch()

        captured = capsys.readouterr()
        assert "DRY-RUN" in captured.out
        assert "wb-patch" in captured.out
        assert "feature/test-branch" in captured.out
        assert "STND" in captured.out

    def test_dry_run_default_values(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run shows default values."""
        state.set_value("branch", "feature/test-branch")
        state.set_value("wb_patch.workbench", "TESR")
        state.set_dry_run(True)

        azure_devops.run_wb_patch()

        captured = capsys.readouterr()
        assert "latest" in captured.out  # default helper_lib_version
        assert "true" in captured.out.lower()  # plan_only default is true

    def test_dry_run_with_all_params(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run with all parameters set."""
        state.set_value("branch", "feature/test-branch")
        state.set_value("wb_patch.workbench", "STND")
        state.set_value("wb_patch.helper_lib_version", "1.2.3")
        state.set_value("wb_patch.plan_only", "false")
        state.set_value("wb_patch.deploy_helper_lib", "true")
        state.set_value("wb_patch.deploy_synapse_dap", "true")
        state.set_value("wb_patch.deploy_fabric_dap", "true")
        state.set_dry_run(True)

        azure_devops.run_wb_patch()

        captured = capsys.readouterr()
        assert "1.2.3" in captured.out
        # plan_only=false should show as false
        assert "Plan Only" in captured.out

    def test_dry_run_shows_org_project(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run shows organization and project."""
        state.set_value("branch", "feature/test-branch")
        state.set_value("wb_patch.workbench", "STND")
        state.set_dry_run(True)

        azure_devops.run_wb_patch()

        captured = capsys.readouterr()
        assert "Org" in captured.out
        assert "Project" in captured.out

    def test_missing_branch(self, temp_state_dir, clear_state_before):
        """Test exits when branch is missing."""
        state.set_value("wb_patch.workbench", "STND")
        state.set_dry_run(True)
        with pytest.raises(SystemExit):
            azure_devops.run_wb_patch()

    def test_missing_workbench(self, temp_state_dir, clear_state_before):
        """Test exits when workbench is missing."""
        state.set_value("branch", "feature/test-branch")
        state.set_dry_run(True)
        with pytest.raises(SystemExit):
            azure_devops.run_wb_patch()

    def test_bool_parsing_string_true(self, temp_state_dir, clear_state_before, capsys):
        """Test boolean parsing with 'true' string."""
        state.set_value("branch", "feature/test-branch")
        state.set_value("wb_patch.workbench", "STND")
        state.set_value("wb_patch.deploy_helper_lib", "true")
        state.set_dry_run(True)

        azure_devops.run_wb_patch()

        captured = capsys.readouterr()
        assert "Deploy Helper Lib" in captured.out

    def test_bool_parsing_string_yes(self, temp_state_dir, clear_state_before, capsys):
        """Test boolean parsing with 'yes' string."""
        state.set_value("branch", "feature/test-branch")
        state.set_value("wb_patch.workbench", "STND")
        state.set_value("wb_patch.deploy_synapse_dap", "yes")
        state.set_dry_run(True)

        azure_devops.run_wb_patch()

        captured = capsys.readouterr()
        assert "Deploy Synapse DAP" in captured.out

    def test_bool_parsing_string_1(self, temp_state_dir, clear_state_before, capsys):
        """Test boolean parsing with '1' string."""
        state.set_value("branch", "feature/test-branch")
        state.set_value("wb_patch.workbench", "STND")
        state.set_value("wb_patch.deploy_fabric_dap", "1")
        state.set_dry_run(True)

        azure_devops.run_wb_patch()

        captured = capsys.readouterr()
        assert "Deploy Fabric DAP" in captured.out
