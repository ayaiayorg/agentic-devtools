"""Tests for _persist_single_var."""

from pathlib import Path
from unittest.mock import patch

from agentic_devtools.cli.setup.commands import _persist_single_var


class TestPersistSingleVar:
    """Tests for _persist_single_var."""

    def test_prints_success_when_persisted(self, tmp_path, capsys):
        """Prints success message when persist_env_var returns True."""
        profile = tmp_path / ".bashrc"
        with patch("agentic_devtools.cli.setup.commands.persist_env_var", return_value=True):
            _persist_single_var(profile, "MY_VAR", "/some/path", "bash", False)
        out = capsys.readouterr().out
        assert "✓ MY_VAR persisted" in out

    def test_prints_already_set_when_skipped_and_exists(self, tmp_path, capsys):
        """Prints 'already set' when persist_env_var returns False and var exists in file."""
        profile = tmp_path / ".bashrc"
        profile.write_text('export MY_VAR="/old/path"\n', encoding="utf-8")
        with patch("agentic_devtools.cli.setup.commands.persist_env_var", return_value=False):
            _persist_single_var(profile, "MY_VAR", "/new/path", "bash", False)
        out = capsys.readouterr().out
        assert "already set" in out
        assert "overwrite-env" in out

    def test_prints_nothing_when_skipped_and_not_in_file(self, tmp_path, capsys):
        """Prints nothing when persist_env_var returns False and var not in file."""
        profile = tmp_path / ".bashrc"
        profile.write_text("# empty\n", encoding="utf-8")
        with patch("agentic_devtools.cli.setup.commands.persist_env_var", return_value=False):
            _persist_single_var(profile, "MY_VAR", "/new/path", "bash", False)
        out = capsys.readouterr().out
        assert "MY_VAR" not in out

    def test_silently_handles_os_error_on_read(self, tmp_path, capsys):
        """Silently catches OSError when reading profile to check existence."""
        profile = tmp_path / ".bashrc"
        with patch("agentic_devtools.cli.setup.commands.persist_env_var", return_value=False):
            with patch.object(Path, "exists", side_effect=OSError("disk error")):
                _persist_single_var(profile, "MY_VAR", "/path", "bash", False)
        # Should not raise
        out = capsys.readouterr().out
        assert "✓" not in out

    def test_prints_nothing_when_file_does_not_exist(self, tmp_path, capsys):
        """Prints nothing extra when persist_env_var returns False and file doesn't exist."""
        profile = tmp_path / "nonexistent" / ".bashrc"
        with patch("agentic_devtools.cli.setup.commands.persist_env_var", return_value=False):
            _persist_single_var(profile, "MY_VAR", "/path", "bash", False)
        out = capsys.readouterr().out
        assert "MY_VAR" not in out
