"""Tests for agentic_devtools.cli.git.agdt_branch._get_parent_sha."""

from unittest.mock import MagicMock

import pytest

from agentic_devtools.cli.git.agdt_branch import GitPlumbingError, _get_parent_sha

_MOD = "agentic_devtools.cli.git.agdt_branch"


class TestGetParentSha:
    """Tests for _get_parent_sha()."""

    def test_returns_parent_sha(self, monkeypatch):
        stdout = "tree abc123\nparent parent_sha_abc\nauthor ...\n"
        mock = MagicMock(returncode=0, stdout=stdout, stderr="")
        monkeypatch.setattr(f"{_MOD}._run_plumbing", lambda *a, **kw: mock)
        assert _get_parent_sha("child") == "parent_sha_abc"

    def test_returns_none_for_root_commit(self, monkeypatch):
        stdout = "tree abc123\nauthor ...\n\ncommit message"
        mock = MagicMock(returncode=0, stdout=stdout, stderr="")
        monkeypatch.setattr(f"{_MOD}._run_plumbing", lambda *a, **kw: mock)
        assert _get_parent_sha("root") is None

    def test_raises_on_cat_file_failure(self, monkeypatch):
        mock = MagicMock(returncode=1, stdout="", stderr="bad object")
        monkeypatch.setattr(f"{_MOD}._run_plumbing", lambda *a, **kw: mock)
        with pytest.raises(GitPlumbingError, match="Failed to read commit object"):
            _get_parent_sha("bad_sha")

    def test_stops_at_blank_line(self, monkeypatch):
        """Parent lines only appear in the header (before the blank line)."""
        stdout = "tree abc123\n\nparent fake_in_body\n"
        mock = MagicMock(returncode=0, stdout=stdout, stderr="")
        monkeypatch.setattr(f"{_MOD}._run_plumbing", lambda *a, **kw: mock)
        assert _get_parent_sha("sha") is None
