"""Tests for inject_python_path_settings."""

import json
import sys
from unittest.mock import patch

from agentic_devtools.cli.workflows.worktree_setup import inject_python_path_settings

_MODULE = "agentic_devtools.cli.workflows.worktree_setup"
_SCRIPTS_DIR = "/usr/local/bin"
_SCRIPTS_DIR_WIN = r"C:\Python312\Scripts"


class TestInjectPythonPathSettings:
    """Tests for inject_python_path_settings function."""

    def test_no_op_when_detect_returns_none(self, tmp_path, capsys):
        """Does nothing when _detect_python_scripts_dir returns None."""
        with patch(f"{_MODULE}._detect_python_scripts_dir", return_value=None):
            inject_python_path_settings(str(tmp_path))

        assert not (tmp_path / ".vscode" / "settings.json").exists()
        captured = capsys.readouterr()
        assert "Warning" in captured.err

    def test_creates_settings_json_without_code_cli(self, tmp_path):
        """Creates .vscode/settings.json even when the code CLI is not on PATH (code CLI not required)."""
        with patch(f"{_MODULE}.is_vscode_available", return_value=False):
            with patch(f"{_MODULE}._detect_python_scripts_dir", return_value=_SCRIPTS_DIR):
                with patch(f"{_MODULE}.sys.platform", "linux"):
                    inject_python_path_settings(str(tmp_path))

        # Settings file should be written regardless of code CLI availability.
        assert (tmp_path / ".vscode" / "settings.json").exists()
        settings = json.loads((tmp_path / ".vscode" / "settings.json").read_text(encoding="utf-8"))
        assert _SCRIPTS_DIR in settings["terminal.integrated.env.linux"]["PATH"]

    def test_creates_settings_json_with_current_platform_key(self, tmp_path):
        """Creates .vscode/settings.json with only the current-platform terminal.integrated.env key."""
        with patch(f"{_MODULE}._detect_python_scripts_dir", return_value=_SCRIPTS_DIR):
            inject_python_path_settings(str(tmp_path))

        settings_path = tmp_path / ".vscode" / "settings.json"
        assert settings_path.exists()
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
        # Exactly one OS key must be present, matching the current platform.
        if sys.platform == "win32":
            assert "terminal.integrated.env.windows" in settings
        elif sys.platform == "darwin":
            assert "terminal.integrated.env.osx" in settings
        else:
            assert "terminal.integrated.env.linux" in settings

    def test_only_injects_windows_key_on_windows(self, tmp_path):
        """On Windows, only terminal.integrated.env.windows is injected."""
        with patch(f"{_MODULE}._detect_python_scripts_dir", return_value=_SCRIPTS_DIR_WIN):
            with patch(f"{_MODULE}.sys.platform", "win32"):
                inject_python_path_settings(str(tmp_path))

        settings = json.loads((tmp_path / ".vscode" / "settings.json").read_text(encoding="utf-8"))
        assert "terminal.integrated.env.windows" in settings
        assert "terminal.integrated.env.linux" not in settings
        assert "terminal.integrated.env.osx" not in settings
        assert _SCRIPTS_DIR_WIN in settings["terminal.integrated.env.windows"]["PATH"]

    def test_only_injects_osx_key_on_macos(self, tmp_path):
        """On macOS, only terminal.integrated.env.osx is injected."""
        with patch(f"{_MODULE}._detect_python_scripts_dir", return_value=_SCRIPTS_DIR):
            with patch(f"{_MODULE}.sys.platform", "darwin"):
                inject_python_path_settings(str(tmp_path))

        settings = json.loads((tmp_path / ".vscode" / "settings.json").read_text(encoding="utf-8"))
        assert "terminal.integrated.env.osx" in settings
        assert "terminal.integrated.env.linux" not in settings
        assert "terminal.integrated.env.windows" not in settings
        assert _SCRIPTS_DIR in settings["terminal.integrated.env.osx"]["PATH"]

    def test_uses_env_path_placeholder_when_no_existing_settings(self, tmp_path):
        """Uses ${env:PATH} as the base PATH value when no settings.json exists."""
        with patch(f"{_MODULE}._detect_python_scripts_dir", return_value=_SCRIPTS_DIR):
            with patch(f"{_MODULE}.sys.platform", "linux"):
                inject_python_path_settings(str(tmp_path))

        settings = json.loads((tmp_path / ".vscode" / "settings.json").read_text(encoding="utf-8"))
        assert "${env:PATH}" in settings["terminal.integrated.env.linux"]["PATH"]

    def test_scripts_dir_prepended_to_path(self, tmp_path):
        """The detected Scripts directory is prepended to PATH for the current platform."""
        with patch(f"{_MODULE}._detect_python_scripts_dir", return_value=_SCRIPTS_DIR):
            with patch(f"{_MODULE}.sys.platform", "linux"):
                inject_python_path_settings(str(tmp_path))

        settings = json.loads((tmp_path / ".vscode" / "settings.json").read_text(encoding="utf-8"))
        assert settings["terminal.integrated.env.linux"]["PATH"].startswith(_SCRIPTS_DIR + ":")

    def test_merges_into_existing_settings_preserving_other_keys(self, tmp_path):
        """Existing settings.json is preserved and PATH is injected."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        existing = {
            "editor.tabSize": 4,
            "terminal.integrated.env.linux": {"MY_VAR": "hello"},
        }
        (vscode_dir / "settings.json").write_text(json.dumps(existing), encoding="utf-8")

        with patch(f"{_MODULE}._detect_python_scripts_dir", return_value=_SCRIPTS_DIR):
            with patch(f"{_MODULE}.sys.platform", "linux"):
                inject_python_path_settings(str(tmp_path))

        settings = json.loads((vscode_dir / "settings.json").read_text(encoding="utf-8"))
        assert settings["editor.tabSize"] == 4
        assert settings["terminal.integrated.env.linux"]["MY_VAR"] == "hello"
        assert _SCRIPTS_DIR in settings["terminal.integrated.env.linux"]["PATH"]

    def test_does_not_duplicate_linux_path_entry(self, tmp_path):
        """Scripts dir is not added to linux PATH if already present (case-sensitive)."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        existing = {
            "terminal.integrated.env.linux": {"PATH": f"{_SCRIPTS_DIR}:${{env:PATH}}"},
        }
        (vscode_dir / "settings.json").write_text(json.dumps(existing), encoding="utf-8")

        with patch(f"{_MODULE}._detect_python_scripts_dir", return_value=_SCRIPTS_DIR):
            with patch(f"{_MODULE}.sys.platform", "linux"):
                inject_python_path_settings(str(tmp_path))

        settings = json.loads((vscode_dir / "settings.json").read_text(encoding="utf-8"))
        path_value = settings["terminal.integrated.env.linux"]["PATH"]
        assert path_value.count(_SCRIPTS_DIR) == 1

    def test_does_not_duplicate_windows_path_entry(self, tmp_path):
        """Scripts dir is not added to Windows PATH if already present."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        existing = {
            "terminal.integrated.env.windows": {"PATH": f"{_SCRIPTS_DIR_WIN};${{env:PATH}}"},
        }
        (vscode_dir / "settings.json").write_text(json.dumps(existing), encoding="utf-8")

        with patch(f"{_MODULE}._detect_python_scripts_dir", return_value=_SCRIPTS_DIR_WIN):
            with patch(f"{_MODULE}.sys.platform", "win32"):
                inject_python_path_settings(str(tmp_path))

        settings = json.loads((vscode_dir / "settings.json").read_text(encoding="utf-8"))
        path_value = settings["terminal.integrated.env.windows"]["PATH"]
        assert path_value.count(_SCRIPTS_DIR_WIN) == 1

    def test_windows_dedup_is_case_insensitive(self, tmp_path):
        """Windows PATH de-duplication is case-insensitive."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        existing = {
            "terminal.integrated.env.windows": {"PATH": r"c:\python312\scripts;${env:PATH}"},
        }
        (vscode_dir / "settings.json").write_text(json.dumps(existing), encoding="utf-8")

        with patch(f"{_MODULE}._detect_python_scripts_dir", return_value=_SCRIPTS_DIR_WIN):
            with patch(f"{_MODULE}.sys.platform", "win32"):
                inject_python_path_settings(str(tmp_path))

        settings = json.loads((vscode_dir / "settings.json").read_text(encoding="utf-8"))
        path_value = settings["terminal.integrated.env.windows"]["PATH"]
        # Should not be added again despite different casing
        assert path_value.lower().count(r"c:\python312\scripts") == 1

    def test_windows_dedup_ignores_segment_whitespace(self, tmp_path):
        """Windows dedup treats leading/trailing segment whitespace as equivalent."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        existing = {
            "terminal.integrated.env.windows": {"PATH": r" c:\python312\scripts ;${env:PATH}"},
        }
        (vscode_dir / "settings.json").write_text(json.dumps(existing), encoding="utf-8")

        with patch(f"{_MODULE}._detect_python_scripts_dir", return_value=_SCRIPTS_DIR_WIN):
            with patch(f"{_MODULE}.sys.platform", "win32"):
                inject_python_path_settings(str(tmp_path))

        settings = json.loads((vscode_dir / "settings.json").read_text(encoding="utf-8"))
        path_value = settings["terminal.integrated.env.windows"]["PATH"]
        assert path_value.lower().count(r"c:\python312\scripts") == 1

    def test_linux_dedup_strips_quotes_around_segments(self, tmp_path, capsys):
        """Linux dedup treats quoted PATH segments as equivalent to unquoted script paths."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        existing = {
            "terminal.integrated.env.linux": {"PATH": '"/usr/local/bin":${env:PATH}'},
        }
        (vscode_dir / "settings.json").write_text(json.dumps(existing), encoding="utf-8")

        with patch(f"{_MODULE}._detect_python_scripts_dir", return_value=_SCRIPTS_DIR):
            with patch(f"{_MODULE}.sys.platform", "linux"):
                inject_python_path_settings(str(tmp_path))

        settings = json.loads((vscode_dir / "settings.json").read_text(encoding="utf-8"))
        path_value = settings["terminal.integrated.env.linux"]["PATH"]
        assert path_value == '"/usr/local/bin":${env:PATH}'
        captured = capsys.readouterr()
        assert "already configured" in captured.out

    def test_linux_dedup_is_case_sensitive(self, tmp_path):
        """Linux PATH de-duplication is case-sensitive (different case = different path)."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        # /USR/LOCAL/BIN is different from /usr/local/bin on Linux
        existing = {
            "terminal.integrated.env.linux": {"PATH": "/USR/LOCAL/BIN:${env:PATH}"},
        }
        (vscode_dir / "settings.json").write_text(json.dumps(existing), encoding="utf-8")

        with patch(f"{_MODULE}._detect_python_scripts_dir", return_value=_SCRIPTS_DIR):
            with patch(f"{_MODULE}.sys.platform", "linux"):
                inject_python_path_settings(str(tmp_path))

        settings = json.loads((vscode_dir / "settings.json").read_text(encoding="utf-8"))
        # /usr/local/bin should be added because /USR/LOCAL/BIN is a different path on Linux
        assert _SCRIPTS_DIR in settings["terminal.integrated.env.linux"]["PATH"]

    def test_handles_corrupt_settings_json(self, tmp_path, capsys):
        """Corrupt settings.json is left untouched (no-op) so JSONC files are preserved."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        original_content = "not valid json"
        (vscode_dir / "settings.json").write_text(original_content, encoding="utf-8")

        with patch(f"{_MODULE}._detect_python_scripts_dir", return_value=_SCRIPTS_DIR):
            inject_python_path_settings(str(tmp_path))

        # File must not be modified — it may be valid JSONC that stdlib json can't parse.
        assert (vscode_dir / "settings.json").read_text(encoding="utf-8") == original_content
        captured = capsys.readouterr()
        assert "Warning" in captured.err

    def test_skips_when_settings_root_is_not_a_dict(self, tmp_path, capsys):
        """No-op when settings.json contains valid JSON but not a root object (e.g. an array)."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        original_content = json.dumps([1, 2, 3])  # valid JSON, but not a dict
        (vscode_dir / "settings.json").write_text(original_content, encoding="utf-8")

        with patch(f"{_MODULE}._detect_python_scripts_dir", return_value=_SCRIPTS_DIR):
            inject_python_path_settings(str(tmp_path))

        # File must not be modified — a non-dict root is invalid for VS Code settings.
        assert (vscode_dir / "settings.json").read_text(encoding="utf-8") == original_content
        captured = capsys.readouterr()
        assert "Warning" in captured.err

    def test_skips_when_env_block_is_not_a_dict(self, tmp_path, capsys):
        """No-op for a platform when its terminal env key exists but is not a JSON object."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        # terminal.integrated.env.linux is a string instead of an object
        existing = {"terminal.integrated.env.linux": "not-an-object"}
        (vscode_dir / "settings.json").write_text(json.dumps(existing), encoding="utf-8")

        with patch(f"{_MODULE}._detect_python_scripts_dir", return_value=_SCRIPTS_DIR):
            with patch(f"{_MODULE}.sys.platform", "linux"):
                inject_python_path_settings(str(tmp_path))

        # Settings file must not be modified.
        assert json.loads((vscode_dir / "settings.json").read_text(encoding="utf-8")) == existing
        captured = capsys.readouterr()
        assert "Warning" in captured.err

    def test_falls_back_when_path_value_is_not_a_string(self, tmp_path, capsys):
        """Falls back to ${env:PATH} and warns when the stored PATH value is not a string."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        # PATH stored as a list instead of a string
        existing = {
            "terminal.integrated.env.linux": {"PATH": ["/some/dir"]},
        }
        (vscode_dir / "settings.json").write_text(json.dumps(existing), encoding="utf-8")

        with patch(f"{_MODULE}._detect_python_scripts_dir", return_value=_SCRIPTS_DIR):
            with patch(f"{_MODULE}.sys.platform", "linux"):
                inject_python_path_settings(str(tmp_path))

        settings = json.loads((vscode_dir / "settings.json").read_text(encoding="utf-8"))
        # Scripts dir should still be injected, using ${env:PATH} as the base.
        injected_path = settings["terminal.integrated.env.linux"]["PATH"]
        assert injected_path.startswith(_SCRIPTS_DIR + ":")
        assert "${env:PATH}" in injected_path
        captured = capsys.readouterr()
        assert "Warning" in captured.err

    def test_handles_oserror_on_write(self, tmp_path, capsys):
        """Write errors are reported as warnings rather than exceptions."""
        with patch(f"{_MODULE}._detect_python_scripts_dir", return_value=_SCRIPTS_DIR):
            with patch("builtins.open", side_effect=OSError("permission denied")):
                inject_python_path_settings(str(tmp_path))

        captured = capsys.readouterr()
        assert "Warning" in captured.err

    def test_already_configured_message_when_dir_already_in_path(self, tmp_path, capsys):
        """Prints 'already configured' when Scripts dir is already in the current platform's PATH."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        existing = {
            "terminal.integrated.env.linux": {"PATH": f"{_SCRIPTS_DIR}:${{env:PATH}}"},
        }
        (vscode_dir / "settings.json").write_text(json.dumps(existing), encoding="utf-8")

        with patch(f"{_MODULE}._detect_python_scripts_dir", return_value=_SCRIPTS_DIR):
            with patch(f"{_MODULE}.sys.platform", "linux"):
                inject_python_path_settings(str(tmp_path))

        captured = capsys.readouterr()
        assert "already configured" in captured.out

    def test_does_not_rewrite_existing_settings_when_already_configured(self, tmp_path):
        """Skips writing settings.json when no changes are needed."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        existing = {
            "editor.tabSize": 4,
            "terminal.integrated.env.linux": {"PATH": f"{_SCRIPTS_DIR}:${{env:PATH}}"},
        }
        (vscode_dir / "settings.json").write_text(json.dumps(existing), encoding="utf-8")

        with patch(f"{_MODULE}._detect_python_scripts_dir", return_value=_SCRIPTS_DIR):
            with patch(f"{_MODULE}.sys.platform", "linux"):
                with patch(f"{_MODULE}.json.dump") as mock_dump:
                    inject_python_path_settings(str(tmp_path))

        mock_dump.assert_not_called()

    def test_cross_platform_runs_regardless_of_os(self, tmp_path):
        """inject_python_path_settings runs on all platforms (not limited to Windows)."""
        with patch(f"{_MODULE}._detect_python_scripts_dir", return_value=_SCRIPTS_DIR):
            inject_python_path_settings(str(tmp_path))

        # Should still create settings.json on Linux
        assert (tmp_path / ".vscode" / "settings.json").exists()
