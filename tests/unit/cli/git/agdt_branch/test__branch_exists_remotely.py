"""Tests for agentic_devtools.cli.git.agdt_branch._branch_exists_remotely."""

from unittest.mock import MagicMock

from agentic_devtools.cli.git.agdt_branch import _branch_exists_remotely

_MOD = "agentic_devtools.cli.git.agdt_branch"


class TestBranchExistsRemotely:
    """Tests for _branch_exists_remotely()."""

    def test_returns_true_when_remote_has_branch(self, monkeypatch):
        mock = MagicMock(returncode=0, stdout="sha refs/heads/b\n", stderr="")
        monkeypatch.setattr(f"{_MOD}._run_plumbing", lambda *a, **kw: mock)
        assert _branch_exists_remotely("b") is True

    def test_returns_false_when_empty_output(self, monkeypatch):
        mock = MagicMock(returncode=0, stdout="", stderr="")
        monkeypatch.setattr(f"{_MOD}._run_plumbing", lambda *a, **kw: mock)
        assert _branch_exists_remotely("b") is False

    def test_returns_false_on_failure(self, monkeypatch):
        mock = MagicMock(returncode=1, stdout="", stderr="error")
        monkeypatch.setattr(f"{_MOD}._run_plumbing", lambda *a, **kw: mock)
        assert _branch_exists_remotely("b") is False
