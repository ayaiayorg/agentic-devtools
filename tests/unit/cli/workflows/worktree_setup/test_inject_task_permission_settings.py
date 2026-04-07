"""Tests for inject_task_permission_settings."""

import json
from unittest.mock import patch

from agentic_devtools.cli.workflows.worktree_setup import inject_task_permission_settings

_MODULE = "agentic_devtools.cli.workflows.worktree_setup"
_SETTING_KEY = "task.allowAutomaticTasks"


class TestInjectTaskPermissionSettings:
    """Tests for inject_task_permission_settings function."""

    def test_creates_settings_json_when_none_exists(self, tmp_path):
        """Creates .vscode/settings.json with task.allowAutomaticTasks set to on."""
        inject_task_permission_settings(str(tmp_path))

        settings_path = tmp_path / ".vscode" / "settings.json"
        assert settings_path.exists()
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
        assert settings[_SETTING_KEY] == "on"

    def test_merges_into_existing_settings_preserving_other_keys(self, tmp_path):
        """Existing settings.json keys are preserved when task.allowAutomaticTasks is added."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        existing = {"editor.tabSize": 4, "editor.fontSize": 14}
        (vscode_dir / "settings.json").write_text(json.dumps(existing), encoding="utf-8")

        inject_task_permission_settings(str(tmp_path))

        settings = json.loads((vscode_dir / "settings.json").read_text(encoding="utf-8"))
        assert settings["editor.tabSize"] == 4
        assert settings["editor.fontSize"] == 14
        assert settings[_SETTING_KEY] == "on"

    def test_no_op_when_already_on(self, tmp_path, capsys):
        """No-op when task.allowAutomaticTasks is already set to on."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        existing = {_SETTING_KEY: "on"}
        (vscode_dir / "settings.json").write_text(json.dumps(existing), encoding="utf-8")

        inject_task_permission_settings(str(tmp_path))

        # File should not be rewritten
        settings = json.loads((vscode_dir / "settings.json").read_text(encoding="utf-8"))
        assert settings[_SETTING_KEY] == "on"
        captured = capsys.readouterr()
        assert "already configured" in captured.out

    def test_no_op_when_already_on_does_not_rewrite(self, tmp_path):
        """Skips writing settings.json when value is already on."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        existing = {_SETTING_KEY: "on"}
        (vscode_dir / "settings.json").write_text(json.dumps(existing), encoding="utf-8")

        with patch(f"{_MODULE}.json.dump") as mock_dump:
            inject_task_permission_settings(str(tmp_path))

        mock_dump.assert_not_called()

    def test_no_op_with_warning_when_off(self, tmp_path, capsys):
        """No-op with warning when task.allowAutomaticTasks is set to off."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        existing = {_SETTING_KEY: "off", "editor.tabSize": 4}
        (vscode_dir / "settings.json").write_text(json.dumps(existing), encoding="utf-8")

        inject_task_permission_settings(str(tmp_path))

        # File should not be modified
        settings = json.loads((vscode_dir / "settings.json").read_text(encoding="utf-8"))
        assert settings[_SETTING_KEY] == "off"
        assert settings["editor.tabSize"] == 4
        captured = capsys.readouterr()
        assert "Warning" in captured.err
        assert "disabled by user choice" in captured.err

    def test_overwrites_auto_with_on(self, tmp_path):
        """Replaces auto value with on."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        existing = {_SETTING_KEY: "auto"}
        (vscode_dir / "settings.json").write_text(json.dumps(existing), encoding="utf-8")

        inject_task_permission_settings(str(tmp_path))

        settings = json.loads((vscode_dir / "settings.json").read_text(encoding="utf-8"))
        assert settings[_SETTING_KEY] == "on"

    def test_sets_value_when_key_missing_from_existing_settings(self, tmp_path):
        """Adds task.allowAutomaticTasks to an existing settings file that lacks it."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        existing = {"editor.tabSize": 4}
        (vscode_dir / "settings.json").write_text(json.dumps(existing), encoding="utf-8")

        inject_task_permission_settings(str(tmp_path))

        settings = json.loads((vscode_dir / "settings.json").read_text(encoding="utf-8"))
        assert settings[_SETTING_KEY] == "on"
        assert settings["editor.tabSize"] == 4

    def test_handles_jsonc_unparseable_json(self, tmp_path, capsys):
        """Warning to stderr and file left untouched when settings.json is unparseable."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        original_content = "// this is JSONC with comments\n{}"
        (vscode_dir / "settings.json").write_text(original_content, encoding="utf-8")

        inject_task_permission_settings(str(tmp_path))

        assert (vscode_dir / "settings.json").read_text(encoding="utf-8") == original_content
        captured = capsys.readouterr()
        assert "Warning" in captured.err

    def test_handles_non_object_root(self, tmp_path, capsys):
        """Warning to stderr and file left untouched when root is not a JSON object."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        original_content = json.dumps([1, 2, 3])
        (vscode_dir / "settings.json").write_text(original_content, encoding="utf-8")

        inject_task_permission_settings(str(tmp_path))

        assert (vscode_dir / "settings.json").read_text(encoding="utf-8") == original_content
        captured = capsys.readouterr()
        assert "Warning" in captured.err
        assert "skipping task permission settings injection" in captured.err

    def test_handles_filesystem_write_error(self, tmp_path, capsys):
        """Write errors are reported as warnings rather than exceptions."""
        with patch("builtins.open", side_effect=OSError("permission denied")):
            inject_task_permission_settings(str(tmp_path))

        captured = capsys.readouterr()
        assert "Warning" in captured.err

    def test_overwrites_unexpected_value(self, tmp_path):
        """Any unexpected value (not on/off) is replaced with on."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        existing = {_SETTING_KEY: "maybe"}
        (vscode_dir / "settings.json").write_text(json.dumps(existing), encoding="utf-8")

        inject_task_permission_settings(str(tmp_path))

        settings = json.loads((vscode_dir / "settings.json").read_text(encoding="utf-8"))
        assert settings[_SETTING_KEY] == "on"

    def test_creates_vscode_directory_if_missing(self, tmp_path, capsys):
        """Creates .vscode/ directory when it does not exist."""
        assert not (tmp_path / ".vscode").exists()

        inject_task_permission_settings(str(tmp_path))

        assert (tmp_path / ".vscode").is_dir()
        settings = json.loads((tmp_path / ".vscode" / "settings.json").read_text(encoding="utf-8"))
        assert settings[_SETTING_KEY] == "on"
        captured = capsys.readouterr()
        assert "Injected task permission settings" in captured.out

    def test_file_ends_with_newline(self, tmp_path):
        """Written settings.json ends with a trailing newline."""
        inject_task_permission_settings(str(tmp_path))

        content = (tmp_path / ".vscode" / "settings.json").read_text(encoding="utf-8")
        assert content.endswith("\n")
