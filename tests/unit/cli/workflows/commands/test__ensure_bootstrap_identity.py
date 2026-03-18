"""Tests for _ensure_bootstrap_identity helper and its integration in initiate_*_workflow functions."""

import os
from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.workflows.commands import _ensure_bootstrap_identity, _ensure_bootstrap_identity_and_scope


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

    For initiate_pull_request_review_workflow and
    initiate_apply_pull_request_review_suggestions_workflow the ordering changed:
    clear is now called first (to prevent stale state from polluting the new
    session), then bootstrap identity/scope is resolved after arg parsing so that
    the worktree_key can be determined from the resolved arguments before any
    state writes occur.

    All other workflow initiation commands retain the original order (ensure → clear).
    """

    def _make_call_recorder(self):
        """Return a list and two side-effect functions that record call order."""
        calls = []
        ensure_mock = MagicMock(side_effect=lambda: calls.append("ensure"))
        clear_mock = MagicMock(side_effect=lambda: calls.append("clear"))
        return calls, ensure_mock, clear_mock

    def test_pull_request_review_calls_clear_before_ensure(self, temp_state_dir, clear_state_before):
        """clear_state_for_workflow_initiation must be called before _ensure_bootstrap_identity.

        The PR review workflow computes the worktree_key from CLI args so that
        state is scoped correctly before any set_value() calls.  This requires
        arg parsing to happen first, which in turn requires the state clear to
        happen before identity resolution (not after).
        """
        from agentic_devtools.cli.workflows import commands

        calls, ensure_mock, clear_mock = self._make_call_recorder()

        with patch.object(commands, "_ensure_bootstrap_identity", ensure_mock):
            with patch.object(commands, "_ensure_bootstrap_identity_and_scope", ensure_mock):
                with patch.object(commands, "clear_state_for_workflow_initiation", clear_mock):
                    with pytest.raises(SystemExit):
                        # Missing required args → exits, but ordering has already happened
                        commands.initiate_pull_request_review_workflow(_argv=[])

        assert calls == ["clear", "ensure"], f"Expected clear before ensure, got: {calls}"

    def test_work_on_jira_issue_calls_ensure_before_clear(self, temp_state_dir, clear_state_before):
        """_ensure_bootstrap_identity must be called before clear_state_for_workflow_initiation."""
        from agentic_devtools.cli.workflows import commands

        calls, ensure_mock, clear_mock = self._make_call_recorder()

        with patch.object(commands, "_ensure_bootstrap_identity", ensure_mock):
            with patch.object(commands, "clear_state_for_workflow_initiation", clear_mock):
                with pytest.raises(SystemExit):
                    commands.initiate_work_on_jira_issue_workflow(_argv=[])

        assert calls == ["ensure", "clear"], f"Expected ensure before clear, got: {calls}"

    def test_apply_pr_suggestions_calls_clear_before_ensure(self, temp_state_dir, clear_state_before):
        """clear_state_for_workflow_initiation must be called before _ensure_bootstrap_identity.

        Same reasoning as for initiate_pull_request_review_workflow: the worktree_key
        is determined from CLI args, so the state clear must precede identity resolution.
        """
        from agentic_devtools.cli.workflows import commands

        calls, ensure_mock, clear_mock = self._make_call_recorder()

        with patch.object(commands, "_ensure_bootstrap_identity", ensure_mock):
            with patch.object(commands, "_ensure_bootstrap_identity_and_scope", ensure_mock):
                with patch.object(commands, "clear_state_for_workflow_initiation", clear_mock):
                    with pytest.raises(SystemExit):
                        commands.initiate_apply_pull_request_review_suggestions_workflow(_argv=[])

        assert calls == ["clear", "ensure"], f"Expected clear before ensure, got: {calls}"

    def test_create_jira_issue_calls_ensure_before_clear(self, temp_state_dir, clear_state_before):
        """_ensure_bootstrap_identity must be called before clear_state_for_workflow_initiation."""
        from agentic_devtools.cli.workflows import commands

        calls, ensure_mock, clear_mock = self._make_call_recorder()

        with patch.object(commands, "_ensure_bootstrap_identity", ensure_mock):
            with patch.object(commands, "clear_state_for_workflow_initiation", clear_mock):
                # This will proceed (no required args), so mock further to avoid real side-effects
                with patch.object(commands, "initiate_workflow"):
                    cp_patch = "agentic_devtools.cli.workflows.worktree_setup.create_placeholder_and_setup_worktree"
                    with patch(cp_patch) as mock_cp:
                        mock_cp.return_value = (False, None)
                        with pytest.raises(SystemExit):
                            commands.initiate_create_jira_issue_workflow(_argv=[])

        assert calls[:2] == ["ensure", "clear"], f"Expected ensure before clear, got: {calls}"

    def test_create_jira_epic_calls_ensure_before_clear(self, temp_state_dir, clear_state_before):
        """_ensure_bootstrap_identity must be called before clear_state_for_workflow_initiation."""
        from agentic_devtools.cli.workflows import commands

        calls, ensure_mock, clear_mock = self._make_call_recorder()

        with patch.object(commands, "_ensure_bootstrap_identity", ensure_mock):
            with patch.object(commands, "clear_state_for_workflow_initiation", clear_mock):
                cp_patch = "agentic_devtools.cli.workflows.worktree_setup.create_placeholder_and_setup_worktree"
                with patch(cp_patch) as mock_cp:
                    mock_cp.return_value = (False, None)
                    with pytest.raises(SystemExit):
                        commands.initiate_create_jira_epic_workflow(_argv=[])

        assert calls[:2] == ["ensure", "clear"], f"Expected ensure before clear, got: {calls}"

    def test_create_jira_subtask_calls_ensure_before_clear(self, temp_state_dir, clear_state_before):
        """_ensure_bootstrap_identity must be called before clear_state_for_workflow_initiation."""
        from agentic_devtools.cli.workflows import commands

        calls, ensure_mock, clear_mock = self._make_call_recorder()

        with patch.object(commands, "_ensure_bootstrap_identity", ensure_mock):
            with patch.object(commands, "clear_state_for_workflow_initiation", clear_mock):
                with pytest.raises(SystemExit):
                    # Missing --parent-key → exits after clear
                    commands.initiate_create_jira_subtask_workflow(_argv=[])

        assert calls[:2] == ["ensure", "clear"], f"Expected ensure before clear, got: {calls}"

    def test_update_jira_issue_calls_ensure_before_clear(self, temp_state_dir, clear_state_before):
        """_ensure_bootstrap_identity must be called before clear_state_for_workflow_initiation."""
        from agentic_devtools.cli.workflows import commands

        calls, ensure_mock, clear_mock = self._make_call_recorder()

        with patch.object(commands, "_ensure_bootstrap_identity", ensure_mock):
            with patch.object(commands, "clear_state_for_workflow_initiation", clear_mock):
                with pytest.raises(SystemExit):
                    commands.initiate_update_jira_issue_workflow(_argv=[])

        assert calls == ["ensure", "clear"], f"Expected ensure before clear, got: {calls}"

    def test_optimize_issue_calls_ensure_before_clear(self, temp_state_dir, clear_state_before):
        """_ensure_bootstrap_identity must be called before clear_state_for_workflow_initiation."""
        from agentic_devtools.cli.workflows import commands

        calls, ensure_mock, clear_mock = self._make_call_recorder()

        with patch.object(commands, "_ensure_bootstrap_identity", ensure_mock):
            with patch.object(commands, "clear_state_for_workflow_initiation", clear_mock):
                with pytest.raises(SystemExit):
                    commands.initiate_optimize_issue_for_ai_agent_workflow(_argv=[])

        assert calls == ["ensure", "clear"], f"Expected ensure before clear, got: {calls}"

    def test_break_down_issue_calls_ensure_before_clear(self, temp_state_dir, clear_state_before):
        """_ensure_bootstrap_identity must be called before clear_state_for_workflow_initiation."""
        from agentic_devtools.cli.workflows import commands

        calls, ensure_mock, clear_mock = self._make_call_recorder()

        with patch.object(commands, "_ensure_bootstrap_identity", ensure_mock):
            with patch.object(commands, "clear_state_for_workflow_initiation", clear_mock):
                with pytest.raises(SystemExit):
                    commands.initiate_break_down_issue_into_subtasks_workflow(_argv=[])

        assert calls == ["ensure", "clear"], f"Expected ensure before clear, got: {calls}"


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
