"""Tests for agentic_devtools.state.delete_pin_file."""

from unittest.mock import patch

from agentic_devtools.state import PIN_FILENAME, delete_pin_file


class TestDeletePinFile:
    """Tests for delete_pin_file function."""

    def test_deletes_existing_pin_file(self, tmp_path):
        """Pin file is deleted when it exists."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        pin_path = agdt_dir / PIN_FILENAME
        pin_path.write_text("{}", encoding="utf-8")

        delete_pin_file(tmp_path)
        assert not pin_path.exists()

    def test_silent_noop_when_absent(self, tmp_path):
        """No error when pin file does not exist."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()

        # Should not raise
        delete_pin_file(tmp_path)

    def test_auto_detects_git_root(self, tmp_path):
        """When git_root is None, auto-detects from _get_git_repo_root."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        pin_path = agdt_dir / PIN_FILENAME
        pin_path.write_text("{}", encoding="utf-8")

        with patch("agentic_devtools.state._get_git_repo_root", return_value=tmp_path):
            delete_pin_file(None)

        assert not pin_path.exists()

    def test_returns_none_when_not_in_git_repo(self):
        """No-op when not in a git repo."""
        with patch("agentic_devtools.state._get_git_repo_root", return_value=None):
            # Should not raise
            delete_pin_file(None)

    def test_ignores_oserror_on_unlink(self, tmp_path):
        """Ignores OSError when attempting to unlink the pin file."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        pin_file = agdt_dir / PIN_FILENAME
        pin_file.touch()

        with patch("pathlib.Path.unlink", side_effect=OSError("mock unlink error")):
            delete_pin_file(tmp_path)

        assert pin_file.exists()
