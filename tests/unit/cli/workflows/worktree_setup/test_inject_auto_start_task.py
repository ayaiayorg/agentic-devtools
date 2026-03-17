"""Tests for inject_auto_start_task."""

import json
from unittest.mock import patch

from agentic_devtools.cli.workflows.worktree_setup import inject_auto_start_task


class TestInjectAutoStartTask:
    """Tests for inject_auto_start_task function."""

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=False)
    def test_returns_false_when_vscode_unavailable(self, mock_available, tmp_path):
        """Returns False without writing anything when VS Code is not on PATH."""
        result = inject_auto_start_task(str(tmp_path), "test prompt")

        assert result is False
        assert not (tmp_path / ".vscode" / "tasks.json").exists()

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_returns_false_when_sentinel_already_exists(self, mock_available, tmp_path):
        """Returns False without writing when the sentinel file already exists."""
        sentinel_dir = tmp_path / ".agdt"
        sentinel_dir.mkdir(parents=True)
        (sentinel_dir / ".copilot-auto-start-triggered").write_text("", encoding="utf-8")

        result = inject_auto_start_task(str(tmp_path), "test prompt")

        assert result is False
        assert not (tmp_path / ".vscode" / "tasks.json").exists()

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_creates_tasks_json_when_absent(self, mock_available, tmp_path):
        """Creates .vscode/tasks.json with the auto-start task when no file exists."""
        result = inject_auto_start_task(str(tmp_path), "hello prompt")

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

        result = inject_auto_start_task(str(tmp_path), "test prompt")

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

        result = inject_auto_start_task(str(tmp_path), "test prompt")

        assert result is True
        data = json.loads((vscode_dir / "tasks.json").read_text(encoding="utf-8"))
        assert len(data["tasks"]) == 1
        captured = capsys.readouterr()
        assert "Warning: could not read" in captured.err

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_returns_true_on_success(self, mock_available, tmp_path):
        """Returns True when the file is written successfully."""
        result = inject_auto_start_task(str(tmp_path), "test prompt")

        assert result is True

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    @patch("builtins.open", side_effect=OSError("disk full"))
    @patch("os.makedirs")
    def test_returns_false_on_write_error(self, mock_makedirs, mock_open, mock_available, tmp_path, capsys):
        """Returns False when writing tasks.json fails."""
        result = inject_auto_start_task(str(tmp_path), "test prompt")

        assert result is False
        captured = capsys.readouterr()
        assert "Warning: could not write" in captured.err

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_task_has_run_on_folder_open(self, mock_available, tmp_path):
        """The injected task has runOn: folderOpen."""
        inject_auto_start_task(str(tmp_path), "test prompt")

        data = json.loads((tmp_path / ".vscode" / "tasks.json").read_text(encoding="utf-8"))
        task = data["tasks"][0]
        assert task["runOptions"]["runOn"] == "folderOpen"

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_task_has_focus_presentation(self, mock_available, tmp_path):
        """The injected task has reveal: always and focus: true."""
        inject_auto_start_task(str(tmp_path), "test prompt")

        data = json.loads((tmp_path / ".vscode" / "tasks.json").read_text(encoding="utf-8"))
        task = data["tasks"][0]
        assert task["presentation"]["reveal"] == "always"
        assert task["presentation"]["focus"] is True

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_command_contains_agdt_copilot_auto_start(self, mock_available, tmp_path):
        """The injected task command invokes agdt-copilot-auto-start."""
        inject_auto_start_task(str(tmp_path), "test prompt")

        data = json.loads((tmp_path / ".vscode" / "tasks.json").read_text(encoding="utf-8"))
        task = data["tasks"][0]
        assert task["command"] == "agdt-copilot-auto-start"

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_task_type_is_process(self, mock_available, tmp_path):
        """The injected task uses type 'process' so no shell quoting is applied."""
        inject_auto_start_task(str(tmp_path), "test prompt")

        data = json.loads((tmp_path / ".vscode" / "tasks.json").read_text(encoding="utf-8"))
        assert data["tasks"][0]["type"] == "process"

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_command_contains_worktree_path(self, mock_available, tmp_path):
        """The injected task args contain --worktree-path."""
        inject_auto_start_task(str(tmp_path), "test prompt")

        data = json.loads((tmp_path / ".vscode" / "tasks.json").read_text(encoding="utf-8"))
        task_args = data["tasks"][0]["args"]
        assert "--worktree-path" in task_args

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_command_contains_start_prompt(self, mock_available, tmp_path):
        """The injected task args contain --start-prompt with the prompt text."""
        inject_auto_start_task(str(tmp_path), "my test prompt")

        data = json.loads((tmp_path / ".vscode" / "tasks.json").read_text(encoding="utf-8"))
        task_args = data["tasks"][0]["args"]
        assert "--start-prompt" in task_args
        assert "my test prompt" in task_args

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_command_contains_created_new_when_file_absent(self, mock_available, tmp_path):
        """The args contain --created-new when tasks.json did not previously exist."""
        inject_auto_start_task(str(tmp_path), "test prompt")

        data = json.loads((tmp_path / ".vscode" / "tasks.json").read_text(encoding="utf-8"))
        task_args = data["tasks"][0]["args"]
        assert "--created-new" in task_args

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_command_does_not_contain_created_new_when_file_preexisted(self, mock_available, tmp_path):
        """The args do NOT contain --created-new when tasks.json already existed."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        existing = {"version": "2.0.0", "tasks": []}
        (vscode_dir / "tasks.json").write_text(json.dumps(existing), encoding="utf-8")

        inject_auto_start_task(str(tmp_path), "test prompt")

        data = json.loads((vscode_dir / "tasks.json").read_text(encoding="utf-8"))
        task_args = data["tasks"][0]["args"]
        assert "--created-new" not in task_args

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_no_platform_specific_shell_options(self, mock_available, tmp_path):
        """The task definition does not set platform-specific shell options."""
        inject_auto_start_task(str(tmp_path), "test prompt")

        data = json.loads((tmp_path / ".vscode" / "tasks.json").read_text(encoding="utf-8"))
        task = data["tasks"][0]
        assert "options" not in task

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_deduplicates_injected_task(self, mock_available, tmp_path):
        """Calling inject twice does not create duplicate tasks."""
        inject_auto_start_task(str(tmp_path), "first prompt")
        inject_auto_start_task(str(tmp_path), "second prompt")

        data = json.loads((tmp_path / ".vscode" / "tasks.json").read_text(encoding="utf-8"))
        auto_start_tasks = [t for t in data["tasks"] if t["label"] == "agdt-copilot-auto-start"]
        assert len(auto_start_tasks) == 1
        # Second call should have the updated args
        assert "second prompt" in auto_start_tasks[0]["args"]

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_handles_existing_tasks_json_without_tasks_key(self, mock_available, tmp_path):
        """Handles an existing tasks.json that has no 'tasks' key."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        (vscode_dir / "tasks.json").write_text(json.dumps({"version": "2.0.0"}), encoding="utf-8")

        result = inject_auto_start_task(str(tmp_path), "test prompt")

        assert result is True
        data = json.loads((vscode_dir / "tasks.json").read_text(encoding="utf-8"))
        assert len(data["tasks"]) == 1

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_custom_task_label(self, mock_available, tmp_path):
        """A custom task label can be provided."""
        result = inject_auto_start_task(str(tmp_path), "test prompt", task_label="my-custom-task")

        assert result is True
        data = json.loads((tmp_path / ".vscode" / "tasks.json").read_text(encoding="utf-8"))
        assert data["tasks"][0]["label"] == "my-custom-task"

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_task_is_not_background(self, mock_available, tmp_path):
        """The injected task is a foreground one-shot command (not background)."""
        inject_auto_start_task(str(tmp_path), "test prompt")

        data = json.loads((tmp_path / ".vscode" / "tasks.json").read_text(encoding="utf-8"))
        task = data["tasks"][0]
        assert "isBackground" not in task
        assert task["problemMatcher"] == []

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_prints_success_message(self, mock_available, tmp_path, capsys):
        """Prints a success message when the task is injected."""
        inject_auto_start_task(str(tmp_path), "test prompt")

        captured = capsys.readouterr()
        assert "Injected auto-start task" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_non_dict_json_top_level_treated_as_malformed(self, mock_available, tmp_path, capsys):
        """A tasks.json containing a JSON array (not object) is overwritten."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        (vscode_dir / "tasks.json").write_text("[1, 2, 3]", encoding="utf-8")

        result = inject_auto_start_task(str(tmp_path), "test prompt")

        assert result is True
        data = json.loads((vscode_dir / "tasks.json").read_text(encoding="utf-8"))
        assert data["version"] == "2.0.0"
        assert len(data["tasks"]) == 1
        captured = capsys.readouterr()
        assert "not a JSON object" in captured.err

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_non_dict_items_in_tasks_array_preserved(self, mock_available, tmp_path):
        """Non-dict items in the tasks array are preserved during dedup."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        existing = {
            "version": "2.0.0",
            "tasks": [
                "a string task",
                42,
                {"label": "build", "type": "shell", "command": "make"},
            ],
        }
        (vscode_dir / "tasks.json").write_text(json.dumps(existing), encoding="utf-8")

        result = inject_auto_start_task(str(tmp_path), "test prompt")

        assert result is True
        data = json.loads((vscode_dir / "tasks.json").read_text(encoding="utf-8"))
        # The two non-dict items + the existing dict task + the new task
        assert len(data["tasks"]) == 4
        assert "a string task" in data["tasks"]
        assert 42 in data["tasks"]

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_returns_false_when_prompt_is_empty(self, mock_available, tmp_path):
        """Returns False when an empty prompt string is provided."""
        result = inject_auto_start_task(str(tmp_path), "")

        assert result is False
        assert not (tmp_path / ".vscode" / "tasks.json").exists()

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_returns_false_when_prompt_is_not_a_string(self, mock_available, tmp_path):
        """Returns False when a non-string prompt is provided."""
        result = inject_auto_start_task(str(tmp_path), 42)  # type: ignore[arg-type]

        assert result is False
        assert not (tmp_path / ".vscode" / "tasks.json").exists()

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_ensures_version_field_when_missing_from_existing(self, mock_available, tmp_path):
        """Adds version field when merging into tasks.json that lacks it."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        existing = {"tasks": [{"label": "existing", "type": "shell", "command": "echo hi"}]}
        (vscode_dir / "tasks.json").write_text(json.dumps(existing), encoding="utf-8")

        inject_auto_start_task(str(tmp_path), "test prompt")

        data = json.loads((vscode_dir / "tasks.json").read_text(encoding="utf-8"))
        assert data["version"] == "2.0.0"
        assert len(data["tasks"]) == 2  # existing + injected

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_sentinel_guard_cleans_up_stale_task_from_tasks_json(self, mock_available, tmp_path):
        """When sentinel exists and tasks.json has the stale task, remove the task entry."""
        # Setup: sentinel exists + tasks.json has the stale auto-start task
        sentinel_dir = tmp_path / ".agdt"
        sentinel_dir.mkdir(parents=True)
        (sentinel_dir / ".copilot-auto-start-triggered").write_text("", encoding="utf-8")
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_data = {
            "version": "2.0.0",
            "tasks": [
                {"label": "agdt-copilot-auto-start", "type": "shell", "command": "agdt-copilot-auto-start"},
                {"label": "user-task", "type": "shell", "command": "echo hi"},
            ],
        }
        (vscode_dir / "tasks.json").write_text(json.dumps(tasks_data), encoding="utf-8")

        result = inject_auto_start_task(str(tmp_path), "test prompt")

        assert result is False
        # The stale task should have been removed; user task preserved
        data = json.loads((vscode_dir / "tasks.json").read_text(encoding="utf-8"))
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["label"] == "user-task"

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_sentinel_guard_deletes_file_when_only_stale_task_remains(self, mock_available, tmp_path):
        """When sentinel exists and tasks.json has only the stale task with --created-new, delete the file."""
        sentinel_dir = tmp_path / ".agdt"
        sentinel_dir.mkdir(parents=True)
        (sentinel_dir / ".copilot-auto-start-triggered").write_text("", encoding="utf-8")
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        # New-format stale task includes --created-new in args
        tasks_data = {
            "version": "2.0.0",
            "tasks": [
                {
                    "label": "agdt-copilot-auto-start",
                    "type": "process",
                    "command": "agdt-copilot-auto-start",
                    "args": ["--worktree-path", str(tmp_path), "--start-prompt", "hello", "--created-new"],
                }
            ],
        }
        (vscode_dir / "tasks.json").write_text(json.dumps(tasks_data), encoding="utf-8")

        result = inject_auto_start_task(str(tmp_path), "test prompt")

        assert result is False
        assert not (vscode_dir / "tasks.json").exists()
        # .vscode/ should be removed too (it's now empty)
        assert not vscode_dir.exists()

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_sentinel_guard_rewrites_file_when_only_stale_task_remains_and_no_created_new(
        self, mock_available, tmp_path
    ):
        """When sentinel exists and the stale task does NOT have --created-new, rewrite instead of delete."""
        sentinel_dir = tmp_path / ".agdt"
        sentinel_dir.mkdir(parents=True)
        (sentinel_dir / ".copilot-auto-start-triggered").write_text("", encoding="utf-8")
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        # Stale task without --created-new (e.g. an old-format task or file pre-existed)
        tasks_data = {
            "version": "2.0.0",
            "tasks": [
                {
                    "label": "agdt-copilot-auto-start",
                    "type": "process",
                    "command": "agdt-copilot-auto-start",
                    "args": ["--worktree-path", str(tmp_path), "--start-prompt", "hello"],
                }
            ],
        }
        (vscode_dir / "tasks.json").write_text(json.dumps(tasks_data), encoding="utf-8")

        result = inject_auto_start_task(str(tmp_path), "test prompt")

        assert result is False
        # File is rewritten (not deleted) because --created-new was absent
        assert (vscode_dir / "tasks.json").exists()
        data = json.loads((vscode_dir / "tasks.json").read_text(encoding="utf-8"))
        assert data["tasks"] == []

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_sentinel_guard_noop_when_no_stale_task(self, mock_available, tmp_path):
        """When sentinel exists but tasks.json has no stale task, leave it untouched."""
        sentinel_dir = tmp_path / ".agdt"
        sentinel_dir.mkdir(parents=True)
        (sentinel_dir / ".copilot-auto-start-triggered").write_text("", encoding="utf-8")
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_data = {
            "version": "2.0.0",
            "tasks": [{"label": "user-task", "type": "shell", "command": "echo hi"}],
        }
        original_content = json.dumps(tasks_data)
        (vscode_dir / "tasks.json").write_text(original_content, encoding="utf-8")

        result = inject_auto_start_task(str(tmp_path), "test prompt")

        assert result is False
        # File should be untouched
        assert (vscode_dir / "tasks.json").read_text(encoding="utf-8") == original_content

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_sentinel_guard_ignores_non_dict_json(self, mock_available, tmp_path):
        """When sentinel exists and tasks.json has a non-dict top-level, leave it alone."""
        sentinel_dir = tmp_path / ".agdt"
        sentinel_dir.mkdir(parents=True)
        (sentinel_dir / ".copilot-auto-start-triggered").write_text("", encoding="utf-8")
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        # tasks.json is a valid JSON list (not a dict)
        (vscode_dir / "tasks.json").write_text("[1, 2, 3]", encoding="utf-8")

        result = inject_auto_start_task(str(tmp_path), "test prompt")

        assert result is False
        # File should be untouched — non-dict top-level is ignored
        assert (vscode_dir / "tasks.json").read_text(encoding="utf-8") == "[1, 2, 3]"

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_sentinel_guard_ignores_non_list_tasks(self, mock_available, tmp_path):
        """When sentinel exists and tasks.json has tasks: null, leave it alone."""
        sentinel_dir = tmp_path / ".agdt"
        sentinel_dir.mkdir(parents=True)
        (sentinel_dir / ".copilot-auto-start-triggered").write_text("", encoding="utf-8")
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_data = {"version": "2.0.0", "tasks": None}
        original = json.dumps(tasks_data)
        (vscode_dir / "tasks.json").write_text(original, encoding="utf-8")

        result = inject_auto_start_task(str(tmp_path), "test prompt")

        assert result is False
        # File should be untouched — non-list tasks is ignored
        assert (vscode_dir / "tasks.json").read_text(encoding="utf-8") == original

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_sentinel_guard_preserves_extra_keys_when_no_tasks_remain(self, mock_available, tmp_path):
        """When sentinel exists, stale task is the only task, but file has extra
        top-level keys (e.g. inputs), rewrite the file instead of deleting."""
        sentinel_dir = tmp_path / ".agdt"
        sentinel_dir.mkdir(parents=True)
        (sentinel_dir / ".copilot-auto-start-triggered").write_text("", encoding="utf-8")
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_data = {
            "version": "2.0.0",
            "tasks": [{"label": "agdt-copilot-auto-start", "type": "shell", "command": "agdt-copilot-auto-start"}],
            "inputs": [{"id": "myInput", "type": "promptString"}],
        }
        (vscode_dir / "tasks.json").write_text(json.dumps(tasks_data), encoding="utf-8")

        result = inject_auto_start_task(str(tmp_path), "test prompt")

        assert result is False
        # File should still exist (has extra keys to preserve)
        assert (vscode_dir / "tasks.json").exists()
        data = json.loads((vscode_dir / "tasks.json").read_text(encoding="utf-8"))
        assert data["tasks"] == []
        assert data["inputs"] == [{"id": "myInput", "type": "promptString"}]

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_sentinel_guard_rmdir_fails_when_vscode_not_empty(self, mock_available, tmp_path):
        """When sentinel exists and tasks.json is deleted but .vscode/ has other
        files, rmdir silently fails and .vscode/ remains."""
        sentinel_dir = tmp_path / ".agdt"
        sentinel_dir.mkdir(parents=True)
        (sentinel_dir / ".copilot-auto-start-triggered").write_text("", encoding="utf-8")
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        # New-format stale task with --created-new so deletion is attempted
        tasks_data = {
            "version": "2.0.0",
            "tasks": [
                {
                    "label": "agdt-copilot-auto-start",
                    "type": "process",
                    "command": "agdt-copilot-auto-start",
                    "args": ["--worktree-path", str(tmp_path), "--start-prompt", "hello", "--created-new"],
                }
            ],
        }
        (vscode_dir / "tasks.json").write_text(json.dumps(tasks_data), encoding="utf-8")
        # Add another file so rmdir fails
        (vscode_dir / "settings.json").write_text("{}", encoding="utf-8")

        result = inject_auto_start_task(str(tmp_path), "test prompt")

        assert result is False
        # tasks.json deleted but .vscode/ remains (has settings.json)
        assert not (vscode_dir / "tasks.json").exists()
        assert vscode_dir.exists()
        assert (vscode_dir / "settings.json").exists()

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_sentinel_guard_ignores_malformed_json(self, mock_available, tmp_path):
        """When sentinel exists and tasks.json has malformed JSON, silently ignore."""
        sentinel_dir = tmp_path / ".agdt"
        sentinel_dir.mkdir(parents=True)
        (sentinel_dir / ".copilot-auto-start-triggered").write_text("", encoding="utf-8")
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        (vscode_dir / "tasks.json").write_text("{invalid json", encoding="utf-8")

        result = inject_auto_start_task(str(tmp_path), "test prompt")

        assert result is False
        # File should be untouched — malformed JSON silently ignored
        assert (vscode_dir / "tasks.json").read_text(encoding="utf-8") == "{invalid json"

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_prompt_with_special_characters_passed_verbatim(self, mock_available, tmp_path):
        """A prompt with spaces and special characters is passed verbatim in args (no shell escaping)."""
        inject_auto_start_task(str(tmp_path), "prompt with $HOME and 'quotes'")

        data = json.loads((tmp_path / ".vscode" / "tasks.json").read_text(encoding="utf-8"))
        task_args = data["tasks"][0]["args"]
        # With process type, the prompt is a plain string element in args — no quoting applied
        assert "prompt with $HOME and 'quotes'" in task_args

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_worktree_path_with_spaces_passed_verbatim(self, mock_available, tmp_path):
        """A worktree path with spaces is passed verbatim in args (no shell escaping)."""
        worktree = tmp_path / "my worktree"
        worktree.mkdir()
        inject_auto_start_task(str(worktree), "test prompt")

        data = json.loads((worktree / ".vscode" / "tasks.json").read_text(encoding="utf-8"))
        task_args = data["tasks"][0]["args"]
        # With process type, the path is a plain string element in args — no quoting applied
        assert str(worktree) in task_args
