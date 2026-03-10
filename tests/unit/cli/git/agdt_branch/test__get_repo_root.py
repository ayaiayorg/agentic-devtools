"""Tests for agentic_devtools.cli.git.agdt_branch._get_repo_root."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from agentic_devtools.cli.git.agdt_branch import GitPlumbingError, _get_repo_root

_MOD = "agentic_devtools.cli.git.agdt_branch"


class TestGetRepoRoot:
    """Tests for _get_repo_root()."""

    def test_returns_path_on_success(self, monkeypatch):
        mock = MagicMock(returncode=0, stdout="/home/user/repo\n", stderr="")
        monkeypatch.setattr(f"{_MOD}._run_plumbing", lambda *a, **kw: mock)
        assert _get_repo_root() == Path("/home/user/repo")

    def test_raises_on_failure(self, monkeypatch):
        mock = MagicMock(returncode=1, stdout="", stderr="not a repo")
        monkeypatch.setattr(f"{_MOD}._run_plumbing", lambda *a, **kw: mock)
        with pytest.raises(GitPlumbingError, match="show-toplevel failed"):
            _get_repo_root()

    def test_raises_on_empty_output(self, monkeypatch):
        mock = MagicMock(returncode=0, stdout="", stderr="")
        monkeypatch.setattr(f"{_MOD}._run_plumbing", lambda *a, **kw: mock)
        with pytest.raises(GitPlumbingError, match="empty output"):
            _get_repo_root()
