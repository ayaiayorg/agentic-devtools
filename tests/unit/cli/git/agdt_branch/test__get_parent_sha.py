"""Tests for agentic_devtools.cli.git.agdt_branch._get_parent_sha."""

from unittest.mock import MagicMock

from agentic_devtools.cli.git.agdt_branch import _get_parent_sha

_MOD = "agentic_devtools.cli.git.agdt_branch"


class TestGetParentSha:
    """Tests for _get_parent_sha()."""

    def test_returns_parent_sha(self, monkeypatch):
        mock = MagicMock(returncode=0, stdout="parent_sha\n", stderr="")
        monkeypatch.setattr(f"{_MOD}._run_plumbing", lambda *a, **kw: mock)
        assert _get_parent_sha("child") == "parent_sha"

    def test_returns_none_on_failure(self, monkeypatch):
        mock = MagicMock(returncode=1, stdout="", stderr="err")
        monkeypatch.setattr(f"{_MOD}._run_plumbing", lambda *a, **kw: mock)
        assert _get_parent_sha("root") is None

    def test_returns_none_on_empty_output(self, monkeypatch):
        mock = MagicMock(returncode=0, stdout="", stderr="")
        monkeypatch.setattr(f"{_MOD}._run_plumbing", lambda *a, **kw: mock)
        assert _get_parent_sha("sha") is None
