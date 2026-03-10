"""Tests for agentic_devtools.cli.git.agdt_branch._read_commit_message."""

from unittest.mock import MagicMock

from agentic_devtools.cli.git.agdt_branch import _read_commit_message

_MOD = "agentic_devtools.cli.git.agdt_branch"


class TestReadCommitMessage:
    """Tests for _read_commit_message()."""

    def test_returns_message_body(self, monkeypatch):
        raw = "tree abc\nauthor A\n\nSubject\n\nBody line"
        mock = MagicMock(returncode=0, stdout=raw, stderr="")
        monkeypatch.setattr(f"{_MOD}._run_plumbing", lambda *a, **kw: mock)
        assert _read_commit_message("sha") == "Subject\n\nBody line"

    def test_returns_empty_on_failure(self, monkeypatch):
        mock = MagicMock(returncode=1, stdout="", stderr="err")
        monkeypatch.setattr(f"{_MOD}._run_plumbing", lambda *a, **kw: mock)
        assert _read_commit_message("sha") == ""

    def test_returns_empty_when_no_blank_line(self, monkeypatch):
        mock = MagicMock(returncode=0, stdout="tree abc\nauthor A", stderr="")
        monkeypatch.setattr(f"{_MOD}._run_plumbing", lambda *a, **kw: mock)
        assert _read_commit_message("sha") == ""
