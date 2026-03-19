"""Tests for _ensure_bootstrap_identity helper and its integration in initiate_*_workflow functions."""

import os
from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.workflows.commands import (
    _ensure_bootstrap_identity,
    _ensure_bootstrap_identity_and_scope,
    _ensure_scoped_bootstrap_and_clear,
)


class TestEnsureBootstrapIdentity:
    """Tests for _ensure_bootstrap_identity()."""

    def test_calls_set_bootstrap_state_when_no_env_override(self, temp_state_dir):
        """Should call set_bootstrap_state() when no env-var override is set."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AGENTIC_DEVTOOLS_STATE_DIR", None)
            os.environ.pop("DFLY_AI_HELPERS_STATE_DIR", None)
            with patch("agentic_devtools.state.set_bootstrap_state") as mock_bootstrap:
                _ensure_bootstrap_identity()
            mock_bootstrap.assert_called_once()

    def test_skips_set_bootstrap_state_when_AGENTIC_DEVTOOLS_STATE_DIR_set(self):
        """Should skip set_bootstrap_state() when AGENTIC_DEVTOOLS_STATE_DIR is set."""
        with patch.dict(os.environ, {"AGENTIC_DEVTOOLS_STATE_DIR": "/some/path"}):
            with patch("agentic_devtools.state.set_bootstrap_state") as mock_bootstrap:
                _ensure_bootstrap_identity()
            mock_bootstrap.assert_not_called()

    def test_skips_set_bootstrap_state_when_DFLY_AI_HELPERS_STATE_DIR_set(self):
        """Should skip set_bootstrap_state() when DFLY_AI_HELPERS_STATE_DIR is set."""
        with patch.dict(os.environ, {"DFLY_AI_HELPERS_STATE_DIR": "/some/path"}):
            with patch("agentic_devtools.state.set_bootstrap_state") as mock_bootstrap:
                _ensure_bootstrap_identity()
            mock_bootstrap.assert_not_called()

    def test_graceful_fallback_on_os_error(self, caplog):
        """Should log a warning and not raise when set_bootstrap_state raises OSError."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AGENTIC_DEVTOOLS_STATE_DIR", None)
            os.environ.pop("DFLY_AI_HELPERS_STATE_DIR", None)
            with patch("agentic_devtools.state.set_bootstrap_state", side_effect=OSError("disk error")):
                import logging

                with caplog.at_level(logging.WARNING, logger="agentic_devtools.cli.workflows.commands"):
                    _ensure_bootstrap_identity()  # must not raise
        assert "Failed to initialize bootstrap state" in caplog.text

    def test_graceful_fallback_on_subprocess_error(self, caplog):
        """Should log a warning and not raise when set_bootstrap_state raises SubprocessError."""
        import subprocess

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AGENTIC_DEVTOOLS_STATE_DIR", None)
            os.environ.pop("DFLY_AI_HELPERS_STATE_DIR", None)
            with patch(
                "agentic_devtools.state.set_bootstrap_state",
                side_effect=subprocess.SubprocessError("git failed"),
            ):
                import logging

                with caplog.at_level(logging.WARNING, logger="agentic_devtools.cli.workflows.commands"):
                    _ensure_bootstrap_identity()  # must not raise
        assert "Failed to initialize bootstrap state" in caplog.text


class TestEnsureBootstrapIdentityCalledBeforeClear:
    """Tests that bootstrap identity is resolved in the correct order relative to
    clear_state_for_workflow_initiation in each initiate_*_workflow function.

    For all workflow initiation commands that accept an issue key, the correct order is:
    1. Parse args (no state I/O)
    2. _ensure_bootstrap_identity_and_scope() — lock state directory scope
    3. clear_state_for_workflow_initiation() — clear in the correctly scoped dir

    This ensures that clear's load_state()/save_state() calls resolve to the
    scoped directory rather than falling back to _unscoped.
    """

    def _make_call_recorder(self):
        """Return a list and two side-effect functions that record call order."""
        calls = []
        ensure_mock = MagicMock(side_effect=lambda *args, **kwargs: calls.append("ensure"))
        clear_mock = MagicMock(side_effect=lambda: calls.append("clear"))
        return calls, ensure_mock, clear_mock

    def test_pull_request_review_calls_ensure_before_clear(self, temp_state_dir, clear_state_before):
        """_ensure_bootstrap_identity_and_scope must be called before clear_state_for_workflow_initiation.

        The PR review workflow parses CLI args first (no state I/O), then calls
        _ensure_bootstrap_identity_and_scope() to lock the state directory scope, and
        ONLY THEN calls clear_state_for_workflow_initiation() so that clear operates
        in the correctly scoped directory (not _unscoped).
        """
        from agentic_devtools.cli.workflows import commands

        calls, ensure_mock, clear_mock = self._make_call_recorder()

        with patch.object(commands, "_ensure_bootstrap_identity", ensure_mock):
            with patch.object(commands, "_ensure_bootstrap_identity_and_scope", ensure_mock):
                with patch.object(commands, "clear_state_for_workflow_initiation", clear_mock):
                    with pytest.raises(SystemExit):
                        # Missing required args → exits, but ordering has already happened
                        commands.initiate_pull_request_review_workflow(_argv=[])

        assert calls == ["ensure", "clear"], f"Expected ensure before clear, got: {calls}"

    def test_work_on_jira_issue_calls_ensure_before_clear(self, temp_state_dir, clear_state_before):
        """_ensure_bootstrap_identity_and_scope must be called before clear_state_for_workflow_initiation."""
        from agentic_devtools.cli.workflows import commands

        calls, ensure_mock, clear_mock = self._make_call_recorder()

        with patch.object(commands, "_ensure_bootstrap_identity", ensure_mock):
            with patch.object(commands, "_ensure_bootstrap_identity_and_scope", ensure_mock):
                with patch.object(commands, "clear_state_for_workflow_initiation", clear_mock):
                    auto_setup_patch = "agentic_devtools.cli.workflows.preflight.perform_auto_setup"
                    with patch(auto_setup_patch, return_value=False):
                        with pytest.raises(SystemExit):
                            commands.initiate_work_on_jira_issue_workflow(_argv=["--issue-key", "DFLY-TEST"])

        assert calls[:2] == ["ensure", "clear"], f"Expected ensure before clear, got: {calls}"

    def test_apply_pr_suggestions_calls_ensure_before_clear(self, temp_state_dir, clear_state_before):
        """_ensure_bootstrap_identity_and_scope must be called before clear_state_for_workflow_initiation.

        Same reasoning as for initiate_pull_request_review_workflow: parse args first (no
        state I/O), lock the scope, then clear in the correctly scoped directory.
        """
        from agentic_devtools.cli.workflows import commands

        calls, ensure_mock, clear_mock = self._make_call_recorder()

        with patch.object(commands, "_ensure_bootstrap_identity", ensure_mock):
            with patch.object(commands, "_ensure_bootstrap_identity_and_scope", ensure_mock):
                with patch.object(commands, "clear_state_for_workflow_initiation", clear_mock):
                    with pytest.raises(SystemExit):
                        commands.initiate_apply_pull_request_review_suggestions_workflow(_argv=[])

        assert calls == ["ensure", "clear"], f"Expected ensure before clear, got: {calls}"

    def test_create_jira_issue_calls_ensure_before_clear(self, temp_state_dir, clear_state_before):
        """_ensure_bootstrap_identity_and_scope must be called before clear_state_for_workflow_initiation."""
        from agentic_devtools.cli.workflows import commands

        calls, ensure_mock, clear_mock = self._make_call_recorder()

        with patch.object(commands, "_ensure_bootstrap_identity", ensure_mock):
            with patch.object(commands, "_ensure_bootstrap_identity_and_scope", ensure_mock):
                with patch.object(commands, "clear_state_for_workflow_initiation", clear_mock):
                    with patch.object(commands, "initiate_workflow"):
                        cp_patch = "agentic_devtools.cli.workflows.worktree_setup.create_placeholder_and_setup_worktree"
                        with patch(cp_patch) as mock_cp:
                            mock_cp.return_value = (False, None)
                            auto_setup_patch = "agentic_devtools.cli.workflows.preflight.perform_auto_setup"
                            with patch(auto_setup_patch, return_value=False):
                                with pytest.raises(SystemExit):
                                    commands.initiate_create_jira_issue_workflow(_argv=["--issue-key", "DFLY-TEST"])

        assert calls[:2] == ["ensure", "clear"], f"Expected ensure before clear, got: {calls}"

    def test_create_jira_epic_calls_ensure_before_clear(self, temp_state_dir, clear_state_before):
        """_ensure_bootstrap_identity_and_scope must be called before clear_state_for_workflow_initiation."""
        from agentic_devtools.cli.workflows import commands

        calls, ensure_mock, clear_mock = self._make_call_recorder()

        with patch.object(commands, "_ensure_bootstrap_identity", ensure_mock):
            with patch.object(commands, "_ensure_bootstrap_identity_and_scope", ensure_mock):
                with patch.object(commands, "clear_state_for_workflow_initiation", clear_mock):
                    cp_patch = "agentic_devtools.cli.workflows.worktree_setup.create_placeholder_and_setup_worktree"
                    with patch(cp_patch) as mock_cp:
                        mock_cp.return_value = (False, None)
                        auto_setup_patch = "agentic_devtools.cli.workflows.preflight.perform_auto_setup"
                        with patch(auto_setup_patch, return_value=False):
                            with pytest.raises(SystemExit):
                                commands.initiate_create_jira_epic_workflow(_argv=["--issue-key", "DFLY-TEST"])

        assert calls[:2] == ["ensure", "clear"], f"Expected ensure before clear, got: {calls}"

    def test_create_jira_subtask_calls_ensure_before_clear(self, temp_state_dir, clear_state_before):
        """_ensure_bootstrap_identity_and_scope must be called before clear_state_for_workflow_initiation."""
        from agentic_devtools.cli.workflows import commands

        calls, ensure_mock, clear_mock = self._make_call_recorder()

        with patch.object(commands, "_ensure_bootstrap_identity", ensure_mock):
            with patch.object(commands, "_ensure_bootstrap_identity_and_scope", ensure_mock):
                with patch.object(commands, "clear_state_for_workflow_initiation", clear_mock):
                    with pytest.raises(SystemExit):
                        commands.initiate_create_jira_subtask_workflow(_argv=["--issue-key", "DFLY-TEST"])

        assert calls[:2] == ["ensure", "clear"], f"Expected ensure before clear, got: {calls}"

    def test_update_jira_issue_calls_ensure_before_clear(self, temp_state_dir, clear_state_before):
        """_ensure_bootstrap_identity_and_scope must be called before clear_state_for_workflow_initiation."""
        from agentic_devtools.cli.workflows import commands

        calls, ensure_mock, clear_mock = self._make_call_recorder()

        with patch.object(commands, "_ensure_bootstrap_identity", ensure_mock):
            with patch.object(commands, "_ensure_bootstrap_identity_and_scope", ensure_mock):
                with patch.object(commands, "clear_state_for_workflow_initiation", clear_mock):
                    auto_setup_patch = "agentic_devtools.cli.workflows.preflight.perform_auto_setup"
                    with patch(auto_setup_patch, return_value=False):
                        with pytest.raises(SystemExit):
                            commands.initiate_update_jira_issue_workflow(_argv=["--issue-key", "DFLY-TEST"])

        assert calls[:2] == ["ensure", "clear"], f"Expected ensure before clear, got: {calls}"

    def test_optimize_issue_calls_ensure_before_clear(self, temp_state_dir, clear_state_before):
        """_ensure_bootstrap_identity_and_scope must be called before clear_state_for_workflow_initiation."""
        from agentic_devtools.cli.workflows import commands

        calls, ensure_mock, clear_mock = self._make_call_recorder()

        with patch.object(commands, "_ensure_bootstrap_identity", ensure_mock):
            with patch.object(commands, "_ensure_bootstrap_identity_and_scope", ensure_mock):
                with patch.object(commands, "clear_state_for_workflow_initiation", clear_mock):
                    auto_setup_patch = "agentic_devtools.cli.workflows.preflight.perform_auto_setup"
                    with patch(auto_setup_patch, return_value=False):
                        with pytest.raises(SystemExit):
                            commands.initiate_optimize_issue_for_ai_agent_workflow(_argv=["--issue-key", "DFLY-TEST"])

        assert calls[:2] == ["ensure", "clear"], f"Expected ensure before clear, got: {calls}"

    def test_break_down_issue_calls_ensure_before_clear(self, temp_state_dir, clear_state_before):
        """_ensure_bootstrap_identity_and_scope must be called before clear_state_for_workflow_initiation."""
        from agentic_devtools.cli.workflows import commands

        calls, ensure_mock, clear_mock = self._make_call_recorder()

        with patch.object(commands, "_ensure_bootstrap_identity", ensure_mock):
            with patch.object(commands, "_ensure_bootstrap_identity_and_scope", ensure_mock):
                with patch.object(commands, "clear_state_for_workflow_initiation", clear_mock):
                    auto_setup_patch = "agentic_devtools.cli.workflows.preflight.perform_auto_setup"
                    with patch(auto_setup_patch, return_value=False):
                        with pytest.raises(SystemExit):
                            commands.initiate_break_down_issue_into_subtasks_workflow(
                                _argv=["--issue-key", "DFLY-TEST"],
                            )

        assert calls[:2] == ["ensure", "clear"], f"Expected ensure before clear, got: {calls}"


class TestEnsureBootstrapIdentityAndScope:
    """Tests for _ensure_bootstrap_identity_and_scope()."""

    def test_calls_set_bootstrap_state_with_worktree_key(self, temp_state_dir):
        """Should call set_bootstrap_state(worktree_key=...) when no env-var override is set."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AGENTIC_DEVTOOLS_STATE_DIR", None)
            os.environ.pop("DFLY_AI_HELPERS_STATE_DIR", None)
            with patch("agentic_devtools.state.set_bootstrap_state") as mock_bootstrap:
                _ensure_bootstrap_identity_and_scope("DFLY-1234")
            mock_bootstrap.assert_called_once_with(worktree_key="DFLY-1234")

    def test_skips_when_AGENTIC_DEVTOOLS_STATE_DIR_set(self):
        """Should skip set_bootstrap_state() when AGENTIC_DEVTOOLS_STATE_DIR is set."""
        with patch.dict(os.environ, {"AGENTIC_DEVTOOLS_STATE_DIR": "/some/path"}):
            with patch("agentic_devtools.state.set_bootstrap_state") as mock_bootstrap:
                _ensure_bootstrap_identity_and_scope("DFLY-1234")
            mock_bootstrap.assert_not_called()

    def test_skips_when_DFLY_AI_HELPERS_STATE_DIR_set(self):
        """Should skip set_bootstrap_state() when DFLY_AI_HELPERS_STATE_DIR is set."""
        with patch.dict(os.environ, {"DFLY_AI_HELPERS_STATE_DIR": "/some/path"}):
            with patch("agentic_devtools.state.set_bootstrap_state") as mock_bootstrap:
                _ensure_bootstrap_identity_and_scope("PR25858")
            mock_bootstrap.assert_not_called()

    def test_graceful_fallback_on_os_error(self, caplog):
        """Should log a warning and not raise when set_bootstrap_state raises OSError."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AGENTIC_DEVTOOLS_STATE_DIR", None)
            os.environ.pop("DFLY_AI_HELPERS_STATE_DIR", None)
            with patch("agentic_devtools.state.set_bootstrap_state", side_effect=OSError("disk error")):
                import logging

                with caplog.at_level(logging.WARNING, logger="agentic_devtools.cli.workflows.commands"):
                    _ensure_bootstrap_identity_and_scope("DFLY-9999")  # must not raise
        assert "Failed to initialize bootstrap state" in caplog.text


class TestEnsureScopedBootstrapAndClear:
    """Tests for _ensure_scoped_bootstrap_and_clear()."""

    def test_uses_scoped_bootstrap_for_normalized_issue_key(self):
        """Should strip issue_key, scope bootstrap, and then clear workflow state."""
        from agentic_devtools.cli.workflows import commands

        with patch.object(commands, "_ensure_bootstrap_identity_and_scope") as scope_mock:
            with patch.object(commands, "_ensure_bootstrap_identity") as identity_mock:
                with patch.object(commands, "clear_state_for_workflow_initiation") as clear_mock:
                    result = _ensure_scoped_bootstrap_and_clear("  DFLY-1234  ")

        assert result == "DFLY-1234"
        scope_mock.assert_called_once_with("DFLY-1234")
        identity_mock.assert_not_called()
        clear_mock.assert_called_once()

    def test_uses_identity_only_when_issue_key_not_provided(self):
        """Should fall back to identity-only bootstrap when issue_key is None."""
        from agentic_devtools.cli.workflows import commands

        with patch.object(commands, "_ensure_bootstrap_identity_and_scope") as scope_mock:
            with patch.object(commands, "_ensure_bootstrap_identity") as identity_mock:
                with patch.object(commands, "clear_state_for_workflow_initiation") as clear_mock:
                    result = _ensure_scoped_bootstrap_and_clear(None)

        assert result is None
        scope_mock.assert_not_called()
        identity_mock.assert_called_once()
        clear_mock.assert_called_once()

    def test_rejects_whitespace_only_issue_key(self, capsys):
        """Should fail fast with a clear message for whitespace-only issue keys."""
        with pytest.raises(SystemExit):
            _ensure_scoped_bootstrap_and_clear("   ")

        captured = capsys.readouterr()
        assert "--issue-key cannot be empty or whitespace-only" in captured.err


class TestEnsureBootstrapIdentityAndScopeCalledWithCorrectValue:
    """Tests that _ensure_bootstrap_identity_and_scope is called with the correct
    stripped issue_key value when --issue-key is provided to each workflow.
    """

    def test_work_on_jira_issue_scope_value(self, temp_state_dir, clear_state_before):
        """initiate_work_on_jira_issue_workflow calls _ensure_bootstrap_identity_and_scope with stripped key."""
        from agentic_devtools.cli.workflows import commands

        with patch.object(commands, "_ensure_bootstrap_identity_and_scope") as scope_mock:
            with patch.object(commands, "clear_state_for_workflow_initiation"):
                auto_setup_patch = "agentic_devtools.cli.workflows.preflight.perform_auto_setup"
                with patch(auto_setup_patch, return_value=False):
                    with pytest.raises(SystemExit):
                        commands.initiate_work_on_jira_issue_workflow(_argv=["--issue-key", "  DFLY-TEST  "])

        scope_mock.assert_called_once_with("DFLY-TEST")

    def test_create_jira_issue_scope_value(self, temp_state_dir, clear_state_before):
        """initiate_create_jira_issue_workflow calls _ensure_bootstrap_identity_and_scope with stripped key."""
        from agentic_devtools.cli.workflows import commands

        with patch.object(commands, "_ensure_bootstrap_identity_and_scope") as scope_mock:
            with patch.object(commands, "clear_state_for_workflow_initiation"):
                with patch.object(commands, "initiate_workflow"):
                    cp_patch = "agentic_devtools.cli.workflows.worktree_setup.create_placeholder_and_setup_worktree"
                    with patch(cp_patch) as mock_cp:
                        mock_cp.return_value = (False, None)
                        auto_setup_patch = "agentic_devtools.cli.workflows.preflight.perform_auto_setup"
                        with patch(auto_setup_patch, return_value=False):
                            with pytest.raises(SystemExit):
                                commands.initiate_create_jira_issue_workflow(_argv=["--issue-key", "  DFLY-TEST  "])

        scope_mock.assert_called_once_with("DFLY-TEST")

    def test_create_jira_epic_scope_value(self, temp_state_dir, clear_state_before):
        """initiate_create_jira_epic_workflow calls _ensure_bootstrap_identity_and_scope with stripped key."""
        from agentic_devtools.cli.workflows import commands

        with patch.object(commands, "_ensure_bootstrap_identity_and_scope") as scope_mock:
            with patch.object(commands, "clear_state_for_workflow_initiation"):
                cp_patch = "agentic_devtools.cli.workflows.worktree_setup.create_placeholder_and_setup_worktree"
                with patch(cp_patch) as mock_cp:
                    mock_cp.return_value = (False, None)
                    auto_setup_patch = "agentic_devtools.cli.workflows.preflight.perform_auto_setup"
                    with patch(auto_setup_patch, return_value=False):
                        with pytest.raises(SystemExit):
                            commands.initiate_create_jira_epic_workflow(_argv=["--issue-key", "  DFLY-TEST  "])

        scope_mock.assert_called_once_with("DFLY-TEST")

    def test_create_jira_subtask_scope_value(self, temp_state_dir, clear_state_before):
        """initiate_create_jira_subtask_workflow calls _ensure_bootstrap_identity_and_scope with stripped key."""
        from agentic_devtools.cli.workflows import commands

        with patch.object(commands, "_ensure_bootstrap_identity_and_scope") as scope_mock:
            with patch.object(commands, "clear_state_for_workflow_initiation"):
                auto_setup_patch = "agentic_devtools.cli.workflows.preflight.perform_auto_setup"
                with patch(auto_setup_patch, return_value=False):
                    with pytest.raises(SystemExit):
                        commands.initiate_create_jira_subtask_workflow(_argv=["--issue-key", "  DFLY-TEST  "])

        scope_mock.assert_called_once_with("DFLY-TEST")

    def test_update_jira_issue_scope_value(self, temp_state_dir, clear_state_before):
        """initiate_update_jira_issue_workflow calls _ensure_bootstrap_identity_and_scope with stripped key."""
        from agentic_devtools.cli.workflows import commands

        with patch.object(commands, "_ensure_bootstrap_identity_and_scope") as scope_mock:
            with patch.object(commands, "clear_state_for_workflow_initiation"):
                auto_setup_patch = "agentic_devtools.cli.workflows.preflight.perform_auto_setup"
                with patch(auto_setup_patch, return_value=False):
                    with pytest.raises(SystemExit):
                        commands.initiate_update_jira_issue_workflow(_argv=["--issue-key", "  DFLY-TEST  "])

        scope_mock.assert_called_once_with("DFLY-TEST")

    def test_optimize_issue_scope_value(self, temp_state_dir, clear_state_before):
        """Calls _ensure_bootstrap_identity_and_scope with stripped key for optimize workflow."""
        from agentic_devtools.cli.workflows import commands

        with patch.object(commands, "_ensure_bootstrap_identity_and_scope") as scope_mock:
            with patch.object(commands, "clear_state_for_workflow_initiation"):
                auto_setup_patch = "agentic_devtools.cli.workflows.preflight.perform_auto_setup"
                with patch(auto_setup_patch, return_value=False):
                    with pytest.raises(SystemExit):
                        commands.initiate_optimize_issue_for_ai_agent_workflow(
                            _argv=["--issue-key", "  DFLY-TEST  "],
                        )

        scope_mock.assert_called_once_with("DFLY-TEST")

    def test_break_down_issue_scope_value(self, temp_state_dir, clear_state_before):
        """Calls _ensure_bootstrap_identity_and_scope with stripped key for break-down workflow."""
        from agentic_devtools.cli.workflows import commands

        with patch.object(commands, "_ensure_bootstrap_identity_and_scope") as scope_mock:
            with patch.object(commands, "clear_state_for_workflow_initiation"):
                auto_setup_patch = "agentic_devtools.cli.workflows.preflight.perform_auto_setup"
                with patch(auto_setup_patch, return_value=False):
                    with pytest.raises(SystemExit):
                        commands.initiate_break_down_issue_into_subtasks_workflow(
                            _argv=["--issue-key", "  DFLY-TEST  "],
                        )

        scope_mock.assert_called_once_with("DFLY-TEST")
