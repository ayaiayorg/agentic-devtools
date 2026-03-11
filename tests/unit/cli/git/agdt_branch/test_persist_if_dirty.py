"""Tests for persist_if_dirty()."""

from subprocess import CompletedProcess
from unittest.mock import patch

from agentic_devtools.cli.git.agdt_branch import (
    PersistResult,
    _reset_dirty,
    is_dirty,
    mark_dirty,
    persist_if_dirty,
)

_MOD = "agentic_devtools.cli.git.agdt_branch"


def _ok(stdout="", stderr=""):
    return CompletedProcess(args=[], returncode=0, stdout=stdout, stderr=stderr)


def _fail(stderr="error", stdout=""):
    return CompletedProcess(args=[], returncode=1, stdout=stdout, stderr=stderr)


class TestPersistIfDirty:
    """Tests for the persist_if_dirty hook."""

    def setup_method(self):
        """Reset dirty flag before each test."""
        _reset_dirty()

    def teardown_method(self):
        """Reset dirty flag after each test."""
        _reset_dirty()

    def test_noop_when_not_dirty(self):
        """Does nothing when the dirty flag is not set."""
        with patch(f"{_MOD}.persist_workflow_state") as mock_persist:
            persist_if_dirty()
        mock_persist.assert_not_called()

    def test_noop_when_no_run_id(self):
        """Does nothing when agdt_run_id is not in state. Resets flag."""
        mark_dirty()
        with patch(f"{_MOD}.get_value", return_value=None):
            with patch(f"{_MOD}.persist_workflow_state") as mock_persist:
                persist_if_dirty()
        mock_persist.assert_not_called()
        assert is_dirty() is False

    def test_calls_persist_when_dirty_with_run_id(self):
        """Calls persist_workflow_state with correct args when dirty."""
        mark_dirty()

        def _get(key, **kw):
            return {
                "agdt_run_id": "abc123def456",
                "versionControl.currentBranch": "feature/DFLY-1234",
            }.get(key)

        mock_result = PersistResult(success=True)
        with patch(f"{_MOD}.get_value", side_effect=_get):
            with patch(f"{_MOD}.persist_workflow_state", return_value=mock_result) as mock_persist:
                with patch("agentic_devtools.state.get_workflow_state", return_value={"active": "review"}):
                    with patch("agentic_devtools.state.is_dry_run", return_value=False):
                        persist_if_dirty()

        mock_persist.assert_called_once_with(
            source_branch="feature/DFLY-1234",
            workflow_type="review",
        )
        assert is_dirty() is False

    def test_resets_flag_even_on_persist_failure(self, capsys):
        """Flag is reset even when persist_workflow_state reports failure."""
        mark_dirty()

        def _get(key, **kw):
            return {
                "agdt_run_id": "abc123def456",
                "versionControl.currentBranch": "main",
            }.get(key)

        fail_result = PersistResult(success=False, error="push failed")
        with patch(f"{_MOD}.get_value", side_effect=_get):
            with patch(f"{_MOD}.persist_workflow_state", return_value=fail_result):
                with patch("agentic_devtools.state.get_workflow_state", return_value=None):
                    with patch("agentic_devtools.state.is_dry_run", return_value=False):
                        persist_if_dirty()  # should not raise

        assert is_dirty() is False
        captured = capsys.readouterr()
        assert "push failed" in captured.err

    def test_silently_ignores_no_workflow_files_error(self, capsys):
        """Treats 'No workflow files found' as a benign no-op (no stderr)."""
        mark_dirty()

        def _get(key, **kw):
            return {
                "agdt_run_id": "abc123def456",
                "versionControl.currentBranch": "main",
            }.get(key)

        no_files_result = PersistResult(
            success=False,
            error="No workflow files found under .agdt/workflows/copilot/DFLY-1234/",
        )
        with patch(f"{_MOD}.get_value", side_effect=_get):
            with patch(f"{_MOD}.persist_workflow_state", return_value=no_files_result):
                with patch("agentic_devtools.state.get_workflow_state", return_value=None):
                    with patch("agentic_devtools.state.is_dry_run", return_value=False):
                        persist_if_dirty()

        assert is_dirty() is False
        captured = capsys.readouterr()
        assert captured.err == ""

    def test_resets_flag_on_exception(self):
        """Flag is reset even when persist_workflow_state raises."""
        mark_dirty()

        def _get(key, **kw):
            return {
                "agdt_run_id": "abc123def456",
                "versionControl.currentBranch": "main",
            }.get(key)

        with patch(f"{_MOD}.get_value", side_effect=_get):
            with patch(f"{_MOD}.persist_workflow_state", side_effect=RuntimeError("boom")):
                with patch("agentic_devtools.state.get_workflow_state", return_value=None):
                    with patch("agentic_devtools.state.is_dry_run", return_value=False):
                        persist_if_dirty()  # should not propagate

        assert is_dirty() is False

    def test_falls_back_to_git_for_branch(self):
        """Uses git rev-parse when versionControl.currentBranch is not set."""
        mark_dirty()

        def _get(key, **kw):
            return {"agdt_run_id": "abc123def456"}.get(key)

        mock_result = PersistResult(success=True)
        with patch(f"{_MOD}.get_value", side_effect=_get):
            with patch(f"{_MOD}._run_plumbing", return_value=_ok(stdout="main\n")):
                with patch(f"{_MOD}.persist_workflow_state", return_value=mock_result) as mock_persist:
                    with patch("agentic_devtools.state.get_workflow_state", return_value=None):
                        with patch("agentic_devtools.state.is_dry_run", return_value=False):
                            persist_if_dirty()

        mock_persist.assert_called_once_with(
            source_branch="main",
            workflow_type="",
        )

    def test_skips_persist_when_branch_unresolvable(self, capsys):
        """Skips persist and logs warning when branch cannot be resolved."""
        mark_dirty()

        def _get(key, **kw):
            return {"agdt_run_id": "abc123def456"}.get(key)

        with patch(f"{_MOD}.get_value", side_effect=_get):
            with patch(f"{_MOD}._run_plumbing", return_value=_fail()):
                with patch(f"{_MOD}.persist_workflow_state") as mock_persist:
                    with patch("agentic_devtools.state.get_workflow_state", return_value=None):
                        with patch("agentic_devtools.state.is_dry_run", return_value=False):
                            persist_if_dirty()

        mock_persist.assert_not_called()
        assert is_dirty() is False
        captured = capsys.readouterr()
        assert "could not resolve source branch" in captured.err

    def test_skips_persist_when_detached_head_in_state(self, capsys):
        """Skips persist when versionControl.currentBranch is 'HEAD'."""
        mark_dirty()

        def _get(key, **kw):
            return {
                "agdt_run_id": "abc123def456",
                "versionControl.currentBranch": "HEAD",
            }.get(key)

        with patch(f"{_MOD}.get_value", side_effect=_get):
            with patch(f"{_MOD}.persist_workflow_state") as mock_persist:
                with patch("agentic_devtools.state.get_workflow_state", return_value=None):
                    with patch("agentic_devtools.state.is_dry_run", return_value=False):
                        persist_if_dirty()

        mock_persist.assert_not_called()
        assert is_dirty() is False
        captured = capsys.readouterr()
        assert "detached HEAD" in captured.err

    def test_skips_persist_when_detached_head_from_git(self, capsys):
        """Skips persist when git rev-parse returns 'HEAD' (detached)."""
        mark_dirty()

        def _get(key, **kw):
            return {"agdt_run_id": "abc123def456"}.get(key)

        with patch(f"{_MOD}.get_value", side_effect=_get):
            with patch(f"{_MOD}._run_plumbing", return_value=_ok(stdout="HEAD\n")):
                with patch(f"{_MOD}.persist_workflow_state") as mock_persist:
                    with patch("agentic_devtools.state.get_workflow_state", return_value=None):
                        with patch("agentic_devtools.state.is_dry_run", return_value=False):
                            persist_if_dirty()

        mock_persist.assert_not_called()
        assert is_dirty() is False
        captured = capsys.readouterr()
        assert "detached HEAD" in captured.err

    def test_dry_run_logs_without_persisting(self, capsys):
        """In dry-run mode, logs a message without calling persist."""
        mark_dirty()

        def _get(key, **kw):
            return {
                "agdt_run_id": "abc123def456",
                "versionControl.currentBranch": "feature/test",
            }.get(key)

        with patch(f"{_MOD}.get_value", side_effect=_get):
            with patch(f"{_MOD}.persist_workflow_state") as mock_persist:
                with patch("agentic_devtools.state.get_workflow_state", return_value=None):
                    with patch("agentic_devtools.state.is_dry_run", return_value=True):
                        persist_if_dirty()

        mock_persist.assert_not_called()
        assert is_dirty() is False
        captured = capsys.readouterr()
        assert "dry-run" in captured.out

    def test_resolves_workflow_type_from_state(self):
        """Reads workflow type from get_workflow_state()."""
        mark_dirty()

        def _get(key, **kw):
            return {
                "agdt_run_id": "abc123def456",
                "versionControl.currentBranch": "feature/test",
            }.get(key)

        mock_result = PersistResult(success=True)
        with patch(f"{_MOD}.get_value", side_effect=_get):
            with patch(f"{_MOD}.persist_workflow_state", return_value=mock_result) as mock_persist:
                with patch(
                    "agentic_devtools.state.get_workflow_state",
                    return_value={"active": "work-on-jira-issue"},
                ):
                    with patch("agentic_devtools.state.is_dry_run", return_value=False):
                        persist_if_dirty()

        mock_persist.assert_called_once_with(
            source_branch="feature/test",
            workflow_type="work-on-jira-issue",
        )

    def test_workflow_type_defaults_to_empty(self):
        """Defaults workflow_type to '' when no workflow is active."""
        mark_dirty()

        def _get(key, **kw):
            return {
                "agdt_run_id": "abc123def456",
                "versionControl.currentBranch": "main",
            }.get(key)

        mock_result = PersistResult(success=True)
        with patch(f"{_MOD}.get_value", side_effect=_get):
            with patch(f"{_MOD}.persist_workflow_state", return_value=mock_result) as mock_persist:
                with patch("agentic_devtools.state.get_workflow_state", return_value=None):
                    with patch("agentic_devtools.state.is_dry_run", return_value=False):
                        persist_if_dirty()

        mock_persist.assert_called_once_with(
            source_branch="main",
            workflow_type="",
        )

    def test_workflow_type_defaults_on_get_workflow_state_exception(self):
        """Defaults workflow_type to '' when get_workflow_state raises an exception."""
        mark_dirty()

        def _get(key, **kw):
            return {
                "agdt_run_id": "abc123def456",
                "versionControl.currentBranch": "main",
            }.get(key)

        mock_result = PersistResult(success=True)
        with patch(f"{_MOD}.get_value", side_effect=_get):
            with patch(f"{_MOD}.persist_workflow_state", return_value=mock_result) as mock_persist:
                with patch(
                    "agentic_devtools.state.get_workflow_state",
                    side_effect=RuntimeError("state corrupted"),
                ):
                    with patch("agentic_devtools.state.is_dry_run", return_value=False):
                        persist_if_dirty()

        mock_persist.assert_called_once_with(
            source_branch="main",
            workflow_type="",
        )
