"""Tests for agentic_devtools.cli.git.agdt_branch._branch_exists_locally."""

from unittest.mock import MagicMock

from agentic_devtools.cli.git.agdt_branch import _branch_exists_locally

_MOD = "agentic_devtools.cli.git.agdt_branch"


class TestBranchExistsLocally:
    """Tests for _branch_exists_locally()."""

    def test_returns_true_when_exists(self, monkeypatch):
        mock = MagicMock(returncode=0, stdout="sha\n", stderr="")
        monkeypatch.setattr(f"{_MOD}._run_plumbing", lambda *a, **kw: mock)
        assert _branch_exists_locally("my-branch") is True

    def test_returns_false_when_missing(self, monkeypatch):
        mock = MagicMock(returncode=1, stdout="", stderr="")
        monkeypatch.setattr(f"{_MOD}._run_plumbing", lambda *a, **kw: mock)
        assert _branch_exists_locally("no-branch") is False
