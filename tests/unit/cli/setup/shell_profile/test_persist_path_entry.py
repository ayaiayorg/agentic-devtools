"""Tests for persist_path_entry."""

from pathlib import Path
from unittest.mock import patch

from agentic_devtools.cli.setup.shell_profile import persist_path_entry


class TestPersistPathEntry:
    """Tests for persist_path_entry."""

    def test_appends_path_for_bash(self, tmp_path):
        """Appends PATH prepend line for bash."""
        profile = tmp_path / ".bashrc"
        profile.write_text("", encoding="utf-8")

        result = persist_path_entry(profile, "/home/user/.agdt/bin", "bash")

        assert result is True
        content = profile.read_text(encoding="utf-8")
        assert "# Added by agdt-setup\n" in content
        assert 'export PATH="/home/user/.agdt/bin:$PATH"\n' in content

    def test_appends_path_for_zsh(self, tmp_path):
        """Appends PATH prepend line for zsh."""
        profile = tmp_path / ".zshrc"
        profile.write_text("# existing\n", encoding="utf-8")

        result = persist_path_entry(profile, "/home/user/.agdt/bin", "zsh")

        assert result is True
        content = profile.read_text(encoding="utf-8")
        assert "# existing" in content
        assert 'export PATH="/home/user/.agdt/bin:$PATH"' in content

    def test_appends_path_for_powershell(self, tmp_path):
        """Appends PATH prepend line for PowerShell."""
        profile = tmp_path / "profile.ps1"
        profile.write_text("", encoding="utf-8")

        result = persist_path_entry(profile, "C:\\Users\\me\\.agdt\\bin", "powershell")

        assert result is True
        content = profile.read_text(encoding="utf-8")
        assert '$env:PATH = "C:\\Users\\me\\.agdt\\bin;$env:PATH"' in content

    def test_skips_when_path_already_present(self, tmp_path):
        """Skips when the path entry is already in the profile."""
        profile = tmp_path / ".bashrc"
        profile.write_text('export PATH="/home/user/.agdt/bin:$PATH"\n', encoding="utf-8")

        result = persist_path_entry(profile, "/home/user/.agdt/bin", "bash", overwrite=False)

        assert result is False

    def test_replaces_when_path_present_and_overwrite(self, tmp_path):
        """Replaces existing PATH line when overwrite=True."""
        profile = tmp_path / ".bashrc"
        profile.write_text(
            '# old\nexport PATH="/home/user/.agdt/bin:$PATH"\n# after\n',
            encoding="utf-8",
        )

        result = persist_path_entry(profile, "/home/user/.agdt/bin", "bash", overwrite=True)

        assert result is True
        content = profile.read_text(encoding="utf-8")
        assert content.count("/home/user/.agdt/bin") == 1
        assert "# after" in content

    def test_returns_false_on_permission_error(self, tmp_path, capsys):
        """Returns False and prints warning on OSError."""
        profile = tmp_path / ".bashrc"

        with patch.object(Path, "read_text", side_effect=PermissionError("denied")):
            with patch.object(Path, "exists", return_value=True):
                result = persist_path_entry(profile, "/some/path", "bash")

        assert result is False
        err = capsys.readouterr().err
        assert "Could not persist PATH entry" in err

    def test_creates_file_when_missing(self, tmp_path):
        """Creates profile file when it doesn't exist."""
        profile = tmp_path / "new_dir" / ".bashrc"

        result = persist_path_entry(profile, "/home/user/.agdt/bin", "bash")

        assert result is True
        assert profile.exists()
        content = profile.read_text(encoding="utf-8")
        assert 'export PATH="/home/user/.agdt/bin:$PATH"' in content

    def test_does_not_match_path_in_comment(self, tmp_path):
        """Does not skip when the path entry appears only in a comment, not a PATH line."""
        profile = tmp_path / ".bashrc"
        profile.write_text("# /home/user/.agdt/bin is a managed dir\n", encoding="utf-8")

        result = persist_path_entry(profile, "/home/user/.agdt/bin", "bash", overwrite=False)

        assert result is True
        content = profile.read_text(encoding="utf-8")
        assert 'export PATH="/home/user/.agdt/bin:$PATH"' in content
