"""Tests for agentic_devtools.cli.git.agdt_branch._read_tree_for_commit."""

from unittest.mock import MagicMock

import pytest

from agentic_devtools.cli.git.agdt_branch import GitPlumbingError, _read_tree_for_commit

_MOD = "agentic_devtools.cli.git.agdt_branch"


class TestReadTreeForCommit:
    """Tests for _read_tree_for_commit()."""

    def test_returns_tree_dict(self, monkeypatch):
        stdout = "100644 blob abc123\tpath/to/file.txt\n100644 blob def456\tother.json\n"
        mock = MagicMock(returncode=0, stdout=stdout, stderr="")
        monkeypatch.setattr(f"{_MOD}._run_plumbing", lambda *a, **kw: mock)
        result = _read_tree_for_commit("sha")
        assert result == {"path/to/file.txt": "abc123", "other.json": "def456"}

    def test_returns_empty_dict_for_empty_tree(self, monkeypatch):
        mock = MagicMock(returncode=0, stdout="", stderr="")
        monkeypatch.setattr(f"{_MOD}._run_plumbing", lambda *a, **kw: mock)
        result = _read_tree_for_commit("sha")
        assert result == {}

    def test_raises_on_failure(self, monkeypatch):
        mock = MagicMock(returncode=1, stdout="", stderr="bad object")
        monkeypatch.setattr(f"{_MOD}._run_plumbing", lambda *a, **kw: mock)
        with pytest.raises(GitPlumbingError, match="ls-tree failed"):
            _read_tree_for_commit("sha")
