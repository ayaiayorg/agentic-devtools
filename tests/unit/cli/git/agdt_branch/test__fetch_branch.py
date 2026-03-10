"""Tests for agentic_devtools.cli.git.agdt_branch._fetch_branch."""

from unittest.mock import MagicMock

from agentic_devtools.cli.git.agdt_branch import _fetch_branch

_MOD = "agentic_devtools.cli.git.agdt_branch"


class TestFetchBranch:
    """Tests for _fetch_branch()."""

    def test_returns_true_on_success(self, monkeypatch):
        mock = MagicMock(returncode=0, stdout="", stderr="")
        monkeypatch.setattr(f"{_MOD}._run_plumbing", lambda *a, **kw: mock)
        assert _fetch_branch("my-branch") is True

    def test_returns_false_on_failure(self, monkeypatch):
        mock = MagicMock(returncode=1, stdout="", stderr="error")
        monkeypatch.setattr(f"{_MOD}._run_plumbing", lambda *a, **kw: mock)
        assert _fetch_branch("my-branch") is False

    def test_calls_fetch_with_correct_refspec(self, monkeypatch):
        calls = []

        def capture(*args, **kwargs):
            calls.append(args)
            return MagicMock(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(f"{_MOD}._run_plumbing", capture)
        _fetch_branch("feat-agdt")
        assert calls == [("fetch", "origin", "feat-agdt:refs/heads/feat-agdt")]
