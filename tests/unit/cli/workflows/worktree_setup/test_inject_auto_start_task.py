"""Tests for inject_auto_start_task."""

import json
from unittest.mock import patch

from agentic_devtools.cli.workflows.worktree_setup import inject_auto_start_task


class TestInjectAutoStartTask:
    """Tests for inject_auto_start_task function."""

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=False)
    def test_returns_false_when_vscode_unavailable(self, mock_available, tmp_path):
        """Returns False without writing anything when VS Code is not on PATH."""
        result = inject_auto_start_task(str(tmp_path), ["copilot", "-i", "test"])

        assert result is False
        assert not (tmp_path / ".vscode" / "tasks.json").exists()

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_creates_tasks_json_when_absent(self, mock_available, tmp_path):
        """Creates .vscode/tasks.json with the auto-start task when no file exists."""
        result = inject_auto_start_task(str(tmp_path), ["copilot", "-i", "hello"])

        assert result is True
        tasks_path = tmp_path / ".vscode" / "tasks.json"
        assert tasks_path.exists()
        data = json.loads(tasks_path.read_text(encoding="utf-8"))
        assert data["version"] == "2.0.0"
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["label"] == "agdt-copilot-auto-start"

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_merges_with_existing_tasks_json(self, mock_available, tmp_path):
        """Preserves existing tasks when merging into an existing tasks.json."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        existing = {
            "version": "2.0.0",
            "tasks": [
                {"label": "build", "type": "shell", "command": "npm run build"},
            ],
        }
        (vscode_dir / "tasks.json").write_text(json.dumps(existing), encoding="utf-8")

        result = inject_auto_start_task(str(tmp_path), ["copilot", "-i", "test"])

        assert result is True
        data = json.loads((vscode_dir / "tasks.json").read_text(encoding="utf-8"))
        labels = [t["label"] for t in data["tasks"]]
        assert "build" in labels
        assert "agdt-copilot-auto-start" in labels
        assert len(data["tasks"]) == 2

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_handles_malformed_existing_tasks_json(self, mock_available, tmp_path, capsys):
        """Overwrites malformed tasks.json with a fresh file."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        (vscode_dir / "tasks.json").write_text("{invalid json", encoding="utf-8")

        result = inject_auto_start_task(str(tmp_path), ["copilot", "-i", "test"])

        assert result is True
        data = json.loads((vscode_dir / "tasks.json").read_text(encoding="utf-8"))
        assert len(data["tasks"]) == 1
        captured = capsys.readouterr()
        assert "Warning: could not read" in captured.err

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_returns_true_on_success(self, mock_available, tmp_path):
        """Returns True when the file is written successfully."""
        result = inject_auto_start_task(str(tmp_path), ["copilot", "-i", "prompt"])

        assert result is True

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    @patch("builtins.open", side_effect=OSError("disk full"))
    @patch("os.makedirs")
    def test_returns_false_on_write_error(self, mock_makedirs, mock_open, mock_available, tmp_path, capsys):
        """Returns False when writing tasks.json fails."""
        result = inject_auto_start_task(str(tmp_path), ["copilot", "-i", "prompt"])

        assert result is False
        captured = capsys.readouterr()
        assert "Warning: could not write" in captured.err

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_task_has_run_on_folder_open(self, mock_available, tmp_path):
        """The injected task has runOn: folderOpen."""
        inject_auto_start_task(str(tmp_path), ["copilot", "-i", "test"])

        data = json.loads((tmp_path / ".vscode" / "tasks.json").read_text(encoding="utf-8"))
        task = data["tasks"][0]
        assert task["runOptions"]["runOn"] == "folderOpen"

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_task_has_focus_presentation(self, mock_available, tmp_path):
        """The injected task has reveal: always and focus: true."""
        inject_auto_start_task(str(tmp_path), ["copilot", "-i", "test"])

        data = json.loads((tmp_path / ".vscode" / "tasks.json").read_text(encoding="utf-8"))
        task = data["tasks"][0]
        assert task["presentation"]["reveal"] == "always"
        assert task["presentation"]["focus"] is True

    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system", return_value="Linux")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_generates_unix_cleanup_command(self, mock_available, mock_system, tmp_path):
        """On Unix the cleanup command uses python3."""
        inject_auto_start_task(str(tmp_path), ["copilot", "-i", "test"])

        data = json.loads((tmp_path / ".vscode" / "tasks.json").read_text(encoding="utf-8"))
        shell_cmd = data["tasks"][0]["command"]
        assert "python3 -c" in shell_cmd

    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system", return_value="Windows")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_generates_windows_cleanup_command(self, mock_available, mock_system, tmp_path):
        """On Windows the cleanup command uses python and the sentinel check uses PowerShell."""
        inject_auto_start_task(str(tmp_path), ["copilot", "-i", "test"])

        data = json.loads((tmp_path / ".vscode" / "tasks.json").read_text(encoding="utf-8"))
        shell_cmd = data["tasks"][0]["command"]
        assert "python -c" in shell_cmd
        assert "Test-Path" in shell_cmd

    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system", return_value="Linux")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_command_checks_sentinel_file(self, mock_available, mock_system, tmp_path):
        """The shell command checks for the sentinel file before executing."""
        inject_auto_start_task(str(tmp_path), ["copilot", "-i", "test"])

        data = json.loads((tmp_path / ".vscode" / "tasks.json").read_text(encoding="utf-8"))
        shell_cmd = data["tasks"][0]["command"]
        assert ".copilot-auto-start-triggered" in shell_cmd
        assert "exit 0" in shell_cmd

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_deduplicates_injected_task(self, mock_available, tmp_path):
        """Calling inject twice does not create duplicate tasks."""
        inject_auto_start_task(str(tmp_path), ["copilot", "-i", "first"])
        inject_auto_start_task(str(tmp_path), ["copilot", "-i", "second"])

        data = json.loads((tmp_path / ".vscode" / "tasks.json").read_text(encoding="utf-8"))
        auto_start_tasks = [t for t in data["tasks"] if t["label"] == "agdt-copilot-auto-start"]
        assert len(auto_start_tasks) == 1
        # Second call should have the updated command
        assert "second" in auto_start_tasks[0]["command"]

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_handles_existing_tasks_json_without_tasks_key(self, mock_available, tmp_path):
        """Handles an existing tasks.json that has no 'tasks' key."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        (vscode_dir / "tasks.json").write_text(json.dumps({"version": "2.0.0"}), encoding="utf-8")

        result = inject_auto_start_task(str(tmp_path), ["copilot", "-i", "test"])

        assert result is True
        data = json.loads((vscode_dir / "tasks.json").read_text(encoding="utf-8"))
        assert len(data["tasks"]) == 1

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_custom_task_label(self, mock_available, tmp_path):
        """A custom task label can be provided."""
        result = inject_auto_start_task(str(tmp_path), ["copilot", "-i", "test"], task_label="my-custom-task")

        assert result is True
        data = json.loads((tmp_path / ".vscode" / "tasks.json").read_text(encoding="utf-8"))
        assert data["tasks"][0]["label"] == "my-custom-task"

    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system", return_value="Linux")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_sentinel_mkdir_in_command(self, mock_available, mock_system, tmp_path):
        """On Unix the command creates the sentinel directory with mkdir -p."""
        inject_auto_start_task(str(tmp_path), ["copilot", "-i", "test"])

        data = json.loads((tmp_path / ".vscode" / "tasks.json").read_text(encoding="utf-8"))
        shell_cmd = data["tasks"][0]["command"]
        assert "mkdir -p" in shell_cmd
        assert "touch" in shell_cmd

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_task_is_background(self, mock_available, tmp_path):
        """The injected task is marked as isBackground."""
        inject_auto_start_task(str(tmp_path), ["copilot", "-i", "test"])

        data = json.loads((tmp_path / ".vscode" / "tasks.json").read_text(encoding="utf-8"))
        task = data["tasks"][0]
        assert task["isBackground"] is True
        assert task["problemMatcher"] == []

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_prints_success_message(self, mock_available, tmp_path, capsys):
        """Prints a success message when the task is injected."""
        inject_auto_start_task(str(tmp_path), ["copilot", "-i", "test"])

        captured = capsys.readouterr()
        assert "Injected auto-start task" in captured.out
