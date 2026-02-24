"""Tests for inject_git_path_settings."""

import json
from unittest.mock import patch

from agentic_devtools.cli.workflows.worktree_setup import inject_git_path_settings


class TestInjectGitPathSettings:
    """Tests for inject_git_path_settings function."""

    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system")
    def test_no_op_on_non_windows(self, mock_system, tmp_path):
        """Test that the function does nothing on non-Windows platforms."""
        mock_system.return_value = "Linux"

        inject_git_path_settings(str(tmp_path))

        assert not (tmp_path / ".vscode" / "settings.json").exists()

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=False)
    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system")
    def test_no_op_when_vscode_not_available(self, mock_system, mock_available, tmp_path, capsys):
        """Test that the function does nothing when VS Code is not on PATH."""
        mock_system.return_value = "Windows"

        inject_git_path_settings(str(tmp_path))

        assert not (tmp_path / ".vscode" / "settings.json").exists()
        captured = capsys.readouterr()
        assert "VS Code not found on PATH" in captured.err

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    @patch("agentic_devtools.cli.workflows.worktree_setup._detect_git_root")
    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system")
    def test_creates_vscode_settings_on_windows(self, mock_system, mock_git_root, mock_available, tmp_path):
        """Test that .vscode/settings.json is created on Windows."""
        mock_system.return_value = "Windows"
        mock_git_root.return_value = r"C:\Program Files\Git"

        inject_git_path_settings(str(tmp_path))

        settings_path = tmp_path / ".vscode" / "settings.json"
        assert settings_path.exists()
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
        path_value = settings["terminal.integrated.env.windows"]["PATH"]
        assert r"C:\Program Files\Git\cmd" in path_value
        assert r"C:\Program Files\Git\usr\bin" in path_value

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    @patch("agentic_devtools.cli.workflows.worktree_setup._detect_git_root")
    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system")
    def test_uses_env_path_placeholder_when_no_existing_settings(
        self, mock_system, mock_git_root, mock_available, tmp_path
    ):
        """Test that ${env:PATH} is used as the base when no settings.json exists."""
        mock_system.return_value = "Windows"
        mock_git_root.return_value = r"C:\Program Files\Git"

        inject_git_path_settings(str(tmp_path))

        settings_path = tmp_path / ".vscode" / "settings.json"
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
        path_value = settings["terminal.integrated.env.windows"]["PATH"]
        assert path_value.startswith("${env:PATH}")

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    @patch("agentic_devtools.cli.workflows.worktree_setup._detect_git_root")
    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system")
    def test_merges_into_existing_settings(self, mock_system, mock_git_root, mock_available, tmp_path):
        """Test that existing settings.json is preserved and PATH is added."""
        mock_system.return_value = "Windows"
        mock_git_root.return_value = r"C:\Program Files\Git"

        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        existing = {"editor.tabSize": 4, "terminal.integrated.env.windows": {"MY_VAR": "hello"}}
        (vscode_dir / "settings.json").write_text(json.dumps(existing), encoding="utf-8")

        inject_git_path_settings(str(tmp_path))

        settings = json.loads((vscode_dir / "settings.json").read_text(encoding="utf-8"))
        assert settings["editor.tabSize"] == 4
        assert settings["terminal.integrated.env.windows"]["MY_VAR"] == "hello"
        assert r"C:\Program Files\Git\cmd" in settings["terminal.integrated.env.windows"]["PATH"]

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    @patch("agentic_devtools.cli.workflows.worktree_setup._detect_git_root")
    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system")
    def test_does_not_duplicate_path_if_already_present(self, mock_system, mock_git_root, mock_available, tmp_path):
        """Test that Git dirs are not added again if both are already in PATH."""
        mock_system.return_value = "Windows"
        mock_git_root.return_value = r"C:\Program Files\Git"

        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        existing = {
            "terminal.integrated.env.windows": {
                "PATH": r"${env:PATH};C:\Program Files\Git\cmd;C:\Program Files\Git\usr\bin"
            }
        }
        (vscode_dir / "settings.json").write_text(json.dumps(existing), encoding="utf-8")

        inject_git_path_settings(str(tmp_path))

        settings = json.loads((vscode_dir / "settings.json").read_text(encoding="utf-8"))
        path_value = settings["terminal.integrated.env.windows"]["PATH"]
        # Both Git dirs should appear exactly once
        assert path_value.count(r"C:\Program Files\Git\cmd") == 1
        assert path_value.count(r"C:\Program Files\Git\usr\bin") == 1

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    @patch("agentic_devtools.cli.workflows.worktree_setup._detect_git_root")
    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system")
    def test_dedup_is_case_insensitive(self, mock_system, mock_git_root, mock_available, tmp_path):
        """Test that already-present dirs are recognised even with different casing."""
        mock_system.return_value = "Windows"
        mock_git_root.return_value = r"C:\Program Files\Git"

        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        # Existing PATH uses different casing for the dirs
        existing = {
            "terminal.integrated.env.windows": {
                "PATH": r"${env:PATH};c:\program files\git\cmd;c:\program files\git\usr\bin"
            }
        }
        (vscode_dir / "settings.json").write_text(json.dumps(existing), encoding="utf-8")

        inject_git_path_settings(str(tmp_path))

        settings = json.loads((vscode_dir / "settings.json").read_text(encoding="utf-8"))
        path_value = settings["terminal.integrated.env.windows"]["PATH"]
        # Dirs must not be added again despite the casing difference
        assert r"C:\Program Files\Git\cmd" not in path_value.split(";")[1:]
        assert r"C:\Program Files\Git\usr\bin" not in path_value.split(";")[1:]

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    @patch("agentic_devtools.cli.workflows.worktree_setup._detect_git_root")
    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system")
    def test_adds_missing_usr_bin_when_only_cmd_present(self, mock_system, mock_git_root, mock_available, tmp_path):
        """Test that usr\\bin is added when only cmd is already in PATH."""
        mock_system.return_value = "Windows"
        mock_git_root.return_value = r"C:\Program Files\Git"

        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        existing = {"terminal.integrated.env.windows": {"PATH": r"${env:PATH};C:\Program Files\Git\cmd"}}
        (vscode_dir / "settings.json").write_text(json.dumps(existing), encoding="utf-8")

        inject_git_path_settings(str(tmp_path))

        settings = json.loads((vscode_dir / "settings.json").read_text(encoding="utf-8"))
        path_value = settings["terminal.integrated.env.windows"]["PATH"]
        # cmd should not be duplicated; usr\bin should be added exactly once
        assert path_value.count(r"C:\Program Files\Git\cmd") == 1
        assert path_value.count(r"C:\Program Files\Git\usr\bin") == 1

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    @patch("agentic_devtools.cli.workflows.worktree_setup._detect_git_root")
    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system")
    def test_adds_missing_cmd_when_only_usr_bin_present(self, mock_system, mock_git_root, mock_available, tmp_path):
        """Test that cmd is added when only usr\\bin is already in PATH."""
        mock_system.return_value = "Windows"
        mock_git_root.return_value = r"C:\Program Files\Git"

        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        existing = {"terminal.integrated.env.windows": {"PATH": r"${env:PATH};C:\Program Files\Git\usr\bin"}}
        (vscode_dir / "settings.json").write_text(json.dumps(existing), encoding="utf-8")

        inject_git_path_settings(str(tmp_path))

        settings = json.loads((vscode_dir / "settings.json").read_text(encoding="utf-8"))
        path_value = settings["terminal.integrated.env.windows"]["PATH"]
        # usr\bin should not be duplicated; cmd should be added exactly once
        assert path_value.count(r"C:\Program Files\Git\cmd") == 1
        assert path_value.count(r"C:\Program Files\Git\usr\bin") == 1

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    @patch("agentic_devtools.cli.workflows.worktree_setup._detect_git_root")
    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system")
    def test_handles_corrupt_settings_json(self, mock_system, mock_git_root, mock_available, tmp_path):
        """Test graceful handling of corrupt settings.json."""
        mock_system.return_value = "Windows"
        mock_git_root.return_value = r"C:\Program Files\Git"

        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        (vscode_dir / "settings.json").write_text("not valid json", encoding="utf-8")

        # Should not raise; should write a fresh settings file
        inject_git_path_settings(str(tmp_path))

        settings = json.loads((vscode_dir / "settings.json").read_text(encoding="utf-8"))
        assert "terminal.integrated.env.windows" in settings

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    @patch("agentic_devtools.cli.workflows.worktree_setup._detect_git_root")
    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system")
    def test_handles_os_error_on_write(self, mock_system, mock_git_root, mock_available, tmp_path, capsys):
        """Test that write errors are reported as warnings rather than exceptions."""
        mock_system.return_value = "Windows"
        mock_git_root.return_value = r"C:\Program Files\Git"

        with patch("builtins.open", side_effect=OSError("permission denied")):
            inject_git_path_settings(str(tmp_path))

        captured = capsys.readouterr()
        assert "Warning" in captured.err
