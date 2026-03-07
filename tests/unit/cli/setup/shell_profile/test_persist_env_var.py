"""Tests for persist_env_var."""

from pathlib import Path
from unittest.mock import patch

from agentic_devtools.cli.setup.shell_profile import persist_env_var


class TestPersistEnvVar:
    """Tests for persist_env_var."""

    def test_appends_export_to_empty_file_bash(self, tmp_path):
        """Appends export line to an empty bash profile."""
        profile = tmp_path / ".bashrc"
        profile.write_text("", encoding="utf-8")

        result = persist_env_var(profile, "MY_VAR", "/some/path", "bash")

        assert result is True
        content = profile.read_text(encoding="utf-8")
        assert "# Added by agdt-setup\n" in content
        assert 'export MY_VAR="/some/path"\n' in content

    def test_appends_export_to_existing_content_zsh(self, tmp_path):
        """Appends export line to file with existing content."""
        profile = tmp_path / ".zshrc"
        profile.write_text("# existing config\nalias ll='ls -la'\n", encoding="utf-8")

        result = persist_env_var(profile, "NODE_EXTRA_CA_CERTS", "/path/to/bundle.pem", "zsh")

        assert result is True
        content = profile.read_text(encoding="utf-8")
        assert "# existing config" in content
        assert "alias ll='ls -la'" in content
        assert "# Added by agdt-setup\n" in content
        assert 'export NODE_EXTRA_CA_CERTS="/path/to/bundle.pem"\n' in content

    def test_skips_when_already_set_no_overwrite(self, tmp_path):
        """Skips when variable already exists and overwrite=False."""
        profile = tmp_path / ".bashrc"
        profile.write_text('export MY_VAR="/old/path"\n', encoding="utf-8")

        result = persist_env_var(profile, "MY_VAR", "/new/path", "bash", overwrite=False)

        assert result is False
        content = profile.read_text(encoding="utf-8")
        assert "/old/path" in content
        assert "/new/path" not in content

    def test_replaces_when_already_set_with_overwrite(self, tmp_path):
        """Replaces existing line when overwrite=True."""
        profile = tmp_path / ".bashrc"
        profile.write_text('# config\nexport MY_VAR="/old/path"\n# more config\n', encoding="utf-8")

        result = persist_env_var(profile, "MY_VAR", "/new/path", "bash", overwrite=True)

        assert result is True
        content = profile.read_text(encoding="utf-8")
        assert "/old/path" not in content
        assert 'export MY_VAR="/new/path"' in content
        assert "# more config" in content

    def test_creates_file_and_dirs_when_missing(self, tmp_path):
        """Creates file and parent directories when they don't exist."""
        profile = tmp_path / "subdir" / "deep" / ".zshrc"

        result = persist_env_var(profile, "MY_VAR", "/some/path", "zsh")

        assert result is True
        assert profile.exists()
        content = profile.read_text(encoding="utf-8")
        assert 'export MY_VAR="/some/path"' in content

    def test_returns_false_on_permission_error(self, tmp_path, capsys):
        """Returns False and prints warning on OSError."""
        profile = tmp_path / ".bashrc"

        with patch.object(Path, "read_text", side_effect=PermissionError("denied")):
            with patch.object(Path, "exists", return_value=True):
                result = persist_env_var(profile, "MY_VAR", "/path", "bash")

        assert result is False
        err = capsys.readouterr().err
        assert "Could not persist MY_VAR" in err

    def test_formats_correctly_for_powershell(self, tmp_path):
        """Formats correctly for PowerShell ($env:VAR = 'value')."""
        profile = tmp_path / "profile.ps1"
        profile.write_text("", encoding="utf-8")

        result = persist_env_var(profile, "MY_VAR", "C:\\Users\\me\\.agdt\\npmrc", "powershell")

        assert result is True
        content = profile.read_text(encoding="utf-8")
        assert '$env:MY_VAR = "C:\\Users\\me\\.agdt\\npmrc"' in content

    def test_powershell_detects_existing_env_var(self, tmp_path):
        """Detects existing PowerShell env var line and skips."""
        profile = tmp_path / "profile.ps1"
        profile.write_text('$env:MY_VAR = "old_value"\n', encoding="utf-8")

        result = persist_env_var(profile, "MY_VAR", "new_value", "powershell", overwrite=False)

        assert result is False

    def test_powershell_replaces_existing_env_var_with_overwrite(self, tmp_path):
        """Replaces existing PowerShell env var line when overwrite=True."""
        profile = tmp_path / "profile.ps1"
        profile.write_text('$env:MY_VAR = "old_value"\n', encoding="utf-8")

        result = persist_env_var(profile, "MY_VAR", "new_value", "powershell", overwrite=True)

        assert result is True
        content = profile.read_text(encoding="utf-8")
        assert "old_value" not in content
        assert '$env:MY_VAR = "new_value"' in content

    def test_detects_var_without_export_bash(self, tmp_path):
        """Detects VAR=... (without export keyword) as existing for bash."""
        profile = tmp_path / ".bashrc"
        profile.write_text('MY_VAR="/old/path"\n', encoding="utf-8")

        result = persist_env_var(profile, "MY_VAR", "/new/path", "bash", overwrite=False)

        assert result is False
        content = profile.read_text(encoding="utf-8")
        assert "/old/path" in content
        assert "/new/path" not in content

    def test_detects_export_var_without_equals(self, tmp_path):
        """Detects 'export VAR' (no assignment) as existing for bash."""
        profile = tmp_path / ".bashrc"
        profile.write_text("export MY_VAR\n", encoding="utf-8")

        result = persist_env_var(profile, "MY_VAR", "/some/path", "bash", overwrite=False)

        assert result is False

    def test_replaces_var_without_export_with_overwrite(self, tmp_path):
        """Replaces VAR=... line when overwrite=True for bash."""
        profile = tmp_path / ".bashrc"
        profile.write_text('MY_VAR="/old/path"\n# after\n', encoding="utf-8")

        result = persist_env_var(profile, "MY_VAR", "/new/path", "bash", overwrite=True)

        assert result is True
        content = profile.read_text(encoding="utf-8")
        assert "/old/path" not in content
        assert 'export MY_VAR="/new/path"' in content
        assert "# after" in content

    def test_escapes_special_chars_in_bash_value(self, tmp_path):
        """Escapes double-quotes, backslashes, dollar signs, and backticks for bash."""
        profile = tmp_path / ".bashrc"
        profile.write_text("", encoding="utf-8")

        result = persist_env_var(profile, "MY_VAR", '/path/with"quotes$var`cmd`', "bash")

        assert result is True
        content = profile.read_text(encoding="utf-8")
        assert 'export MY_VAR="/path/with\\"quotes\\$var\\`cmd\\`"' in content

    def test_escapes_special_chars_in_powershell_value(self, tmp_path):
        """Escapes double-quotes, dollar signs, and backticks for PowerShell."""
        profile = tmp_path / "profile.ps1"
        profile.write_text("", encoding="utf-8")

        result = persist_env_var(profile, "MY_VAR", 'C:\\path"with$var`cmd`', "powershell")

        assert result is True
        content = profile.read_text(encoding="utf-8")
        assert '$env:MY_VAR = "C:\\path`"with`$var``cmd``"' in content

    def test_appends_newline_when_last_line_has_no_trailing_newline(self, tmp_path):
        """Inserts a newline before appending when the file doesn't end with one."""
        profile = tmp_path / ".bashrc"
        # Write content WITHOUT a trailing newline
        profile.write_text("# existing config", encoding="utf-8")

        result = persist_env_var(profile, "MY_VAR", "/some/path", "bash")

        assert result is True
        content = profile.read_text(encoding="utf-8")
        # Verify there's a newline between existing content and the new line
        assert "# existing config\n# Added by agdt-setup\n" in content
        assert 'export MY_VAR="/some/path"' in content
