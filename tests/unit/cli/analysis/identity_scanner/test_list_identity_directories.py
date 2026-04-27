"""Tests for list_identity_directories()."""

from __future__ import annotations

from unittest.mock import patch

from agentic_devtools.cli.analysis.identity_scanner import (
    IdentityDir,
    list_identity_directories,
)


class TestListIdentityDirectories:
    """Tests for listing identity directories."""

    def test_multiple_identities_listed(self, tmp_path):
        """All non-_unscoped identity dirs are listed."""
        wf = tmp_path / ".agdt" / "workflows"
        (wf / "alice").mkdir(parents=True)
        (wf / "bob").mkdir(parents=True)

        result = list_identity_directories(tmp_path)
        assert len(result) == 2
        names = [r.name for r in result]
        assert names == ["alice", "bob"]
        assert all(isinstance(r, IdentityDir) for r in result)

    def test_empty_workflows_dir(self, tmp_path):
        """Empty workflows dir → empty list."""
        (tmp_path / ".agdt" / "workflows").mkdir(parents=True)
        result = list_identity_directories(tmp_path)
        assert result == []

    def test_missing_identity_owner_returns_none(self, tmp_path):
        """Missing .identity-owner → owner_email is None."""
        wf = tmp_path / ".agdt" / "workflows"
        (wf / "alice").mkdir(parents=True)

        result = list_identity_directories(tmp_path)
        assert result[0].owner_email is None

    def test_identity_owner_read(self, tmp_path):
        """Present .identity-owner → owner_email is populated."""
        wf = tmp_path / ".agdt" / "workflows"
        (wf / "alice").mkdir(parents=True)
        (wf / "alice" / ".identity-owner").write_text("alice@example.com", encoding="utf-8")

        result = list_identity_directories(tmp_path)
        assert result[0].owner_email == "alice@example.com"

    def test_unscoped_excluded(self, tmp_path):
        """_unscoped is excluded from results."""
        wf = tmp_path / ".agdt" / "workflows"
        (wf / "_unscoped").mkdir(parents=True)
        (wf / "alice").mkdir(parents=True)

        result = list_identity_directories(tmp_path)
        assert len(result) == 1
        assert result[0].name == "alice"

    def test_missing_workflows_dir(self, tmp_path):
        """No .agdt/workflows/ → empty list."""
        result = list_identity_directories(tmp_path)
        assert result == []

    def test_permission_error_on_iterdir_returns_empty(self, tmp_path):
        """PermissionError when iterating workflows dir → empty list."""
        wf = tmp_path / ".agdt" / "workflows"
        wf.mkdir(parents=True)
        (wf / "alice").mkdir()

        with patch.object(type(wf), "iterdir", side_effect=PermissionError("denied")):
            result = list_identity_directories(tmp_path)
        assert result == []

    def test_non_dir_entry_skipped(self, tmp_path):
        """Regular files in workflows/ are skipped."""
        wf = tmp_path / ".agdt" / "workflows"
        wf.mkdir(parents=True)
        (wf / "some_file.txt").write_text("not a dir", encoding="utf-8")
        (wf / "alice").mkdir()

        result = list_identity_directories(tmp_path)
        assert len(result) == 1
        assert result[0].name == "alice"

    def test_unsafe_dir_name_skipped(self, tmp_path):
        """Identity dirs with unsafe names are skipped."""
        wf = tmp_path / ".agdt" / "workflows"
        (wf / "alice").mkdir(parents=True)
        # Name with a space is rejected by is_safe_dir_segment
        (wf / "bad name").mkdir(parents=True)

        result = list_identity_directories(tmp_path)
        assert len(result) == 1
        assert result[0].name == "alice"

    def test_os_error_reading_owner_file_returns_none_email(self, tmp_path):
        """OSError reading .identity-owner → owner_email is None."""
        wf = tmp_path / ".agdt" / "workflows"
        (wf / "alice").mkdir(parents=True)
        owner_file = wf / "alice" / ".identity-owner"
        owner_file.write_text("alice@example.com", encoding="utf-8")

        with patch("pathlib.Path.read_text", side_effect=OSError("cannot read")):
            result = list_identity_directories(tmp_path)
        assert result[0].owner_email is None
