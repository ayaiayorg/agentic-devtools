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
    def test_task_is_not_background(self, mock_available, tmp_path):
        """The injected task is a foreground one-shot command (not background)."""
        inject_auto_start_task(str(tmp_path), ["copilot", "-i", "test"])

        data = json.loads((tmp_path / ".vscode" / "tasks.json").read_text(encoding="utf-8"))
        task = data["tasks"][0]
        assert "isBackground" not in task
        assert task["problemMatcher"] == []

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_prints_success_message(self, mock_available, tmp_path, capsys):
        """Prints a success message when the task is injected."""
        inject_auto_start_task(str(tmp_path), ["copilot", "-i", "test"])

        captured = capsys.readouterr()
        assert "Injected auto-start task" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system", return_value="Windows")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_windows_quotes_args_with_spaces(self, mock_available, mock_system, tmp_path):
        """On Windows, command args containing spaces are single-quoted."""
        inject_auto_start_task(str(tmp_path), ["copilot", "-i", "prompt with spaces"])

        data = json.loads((tmp_path / ".vscode" / "tasks.json").read_text(encoding="utf-8"))
        shell_cmd = data["tasks"][0]["command"]
        assert "'prompt with spaces'" in shell_cmd

    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system", return_value="Windows")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_windows_task_has_explicit_powershell_shell(self, mock_available, mock_system, tmp_path):
        """On Windows the task specifies PowerShell as the explicit shell."""
        inject_auto_start_task(str(tmp_path), ["copilot", "-i", "test"])

        data = json.loads((tmp_path / ".vscode" / "tasks.json").read_text(encoding="utf-8"))
        task = data["tasks"][0]
        assert "options" in task
        assert task["options"]["shell"]["executable"] == "powershell.exe"
        assert task["options"]["shell"]["args"] == ["-Command"]

    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system", return_value="Linux")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_unix_removes_sentinel_on_command_failure(self, mock_available, mock_system, tmp_path):
        """On Unix the sentinel is removed when the command exits non-zero."""
        inject_auto_start_task(str(tmp_path), ["copilot", "-i", "test"])

        data = json.loads((tmp_path / ".vscode" / "tasks.json").read_text(encoding="utf-8"))
        shell_cmd = data["tasks"][0]["command"]
        assert "agdt_exit=$?" in shell_cmd
        assert "rm -f" in shell_cmd

    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system", return_value="Windows")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_windows_removes_sentinel_on_command_failure(self, mock_available, mock_system, tmp_path):
        """On Windows the sentinel is removed when the command exits non-zero."""
        inject_auto_start_task(str(tmp_path), ["copilot", "-i", "test"])

        data = json.loads((tmp_path / ".vscode" / "tasks.json").read_text(encoding="utf-8"))
        shell_cmd = data["tasks"][0]["command"]
        assert "$agdtExit=$LASTEXITCODE" in shell_cmd
        assert "Remove-Item" in shell_cmd

    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system", return_value="Linux")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_linux_task_has_no_shell_options(self, mock_available, mock_system, tmp_path):
        """On Linux the task does not set explicit shell options."""
        inject_auto_start_task(str(tmp_path), ["copilot", "-i", "test"])

        data = json.loads((tmp_path / ".vscode" / "tasks.json").read_text(encoding="utf-8"))
        task = data["tasks"][0]
        assert "options" not in task

    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system", return_value="Linux")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_cleanup_uses_repr_for_path_safety(self, mock_available, mock_system, tmp_path):
        """The cleanup one-liner uses repr() for safe embedding of paths."""
        inject_auto_start_task(str(tmp_path), ["copilot", "-i", "test"])

        data = json.loads((tmp_path / ".vscode" / "tasks.json").read_text(encoding="utf-8"))
        shell_cmd = data["tasks"][0]["command"]
        # repr() wraps strings in quotes; the cleanup command should contain
        # encoding='utf-8' for safe file I/O
        assert "encoding='utf-8'" in shell_cmd

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_non_dict_json_top_level_treated_as_malformed(self, mock_available, tmp_path, capsys):
        """A tasks.json containing a JSON array (not object) is overwritten."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        (vscode_dir / "tasks.json").write_text("[1, 2, 3]", encoding="utf-8")

        result = inject_auto_start_task(str(tmp_path), ["copilot", "-i", "test"])

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

        result = inject_auto_start_task(str(tmp_path), ["copilot", "-i", "test"])

        assert result is True
        data = json.loads((vscode_dir / "tasks.json").read_text(encoding="utf-8"))
        # The two non-dict items + the existing dict task + the new task
        assert len(data["tasks"]) == 4
        assert "a string task" in data["tasks"]
        assert 42 in data["tasks"]

    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system", return_value="Linux")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_cleanup_one_liner_preserves_non_dict_items(self, mock_available, mock_system, tmp_path):
        """The cleanup one-liner keeps non-dict items and only removes matching dicts."""
        inject_auto_start_task(str(tmp_path), ["copilot", "-i", "test"])

        data = json.loads((tmp_path / ".vscode" / "tasks.json").read_text(encoding="utf-8"))
        shell_cmd = data["tasks"][0]["command"]
        # The cleanup filter must use 'not isinstance(t,dict) or ...' so
        # non-dict items are preserved — not 'isinstance(t,dict) and ...'
        # which would drop them.
        assert "not isinstance(t,dict)" in shell_cmd

    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system", return_value="Linux")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_cleanup_escapes_double_quotes_from_repr(self, mock_available, mock_system, tmp_path):
        """Double quotes produced by repr() are escaped in the -c argument."""
        # Use a task label containing a single quote to force repr() to produce "..."
        inject_auto_start_task(str(tmp_path), ["copilot", "-i", "test"], task_label="it's a label")

        data = json.loads((tmp_path / ".vscode" / "tasks.json").read_text(encoding="utf-8"))
        shell_cmd = data["tasks"][0]["command"]
        # The cleanup -c "..." argument must not contain unescaped double quotes.
        # repr("it's a label") → '"it\'s a label"' — the outer " must be escaped
        # to \" so the shell sees: python3 -c "...!=\"it\'s a label\"..."
        assert 'python3 -c "' in shell_cmd
        # After JSON round-trip, the escaped \" appear as literal \"
        assert '\\"it' in shell_cmd
        assert 'a label\\"' in shell_cmd

    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system", return_value="Windows")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_windows_always_quotes_simple_args(self, mock_available, mock_system, tmp_path):
        """On Windows, all args are quoted even without spaces or special chars."""
        inject_auto_start_task(str(tmp_path), ["copilot", "-i", "test"])

        data = json.loads((tmp_path / ".vscode" / "tasks.json").read_text(encoding="utf-8"))
        shell_cmd = data["tasks"][0]["command"]
        # Every argument should be single-quoted in PowerShell
        assert "'copilot'" in shell_cmd
        assert "'-i'" in shell_cmd
        assert "'test'" in shell_cmd

    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system", return_value="Windows")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_windows_uses_call_operator(self, mock_available, mock_system, tmp_path):
        """On Windows, the command uses the & call operator for execution."""
        inject_auto_start_task(str(tmp_path), ["copilot", "-i", "test"])

        data = json.loads((tmp_path / ".vscode" / "tasks.json").read_text(encoding="utf-8"))
        shell_cmd = data["tasks"][0]["command"]
        # The & call operator must precede the quoted command so PowerShell
        # treats it as an executable invocation, not a string literal.
        assert "& 'copilot'" in shell_cmd

    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system", return_value="Windows")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_windows_cleanup_uses_backtick_escaping(self, mock_available, mock_system, tmp_path):
        """On Windows, double quotes in the cleanup -c arg use backtick escaping."""
        # Use a label with a single quote to force repr() to produce "..."
        inject_auto_start_task(str(tmp_path), ["copilot", "-i", "test"], task_label="it's a label")

        data = json.loads((tmp_path / ".vscode" / "tasks.json").read_text(encoding="utf-8"))
        shell_cmd = data["tasks"][0]["command"]
        # PowerShell uses `" (backtick-double-quote) for escaping, not \"
        assert "python -c" in shell_cmd
        assert '`"' in shell_cmd
        # Must NOT contain bash-style backslash escaping
        assert '\\"' not in shell_cmd

    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system", return_value="Linux")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_unix_sentinel_uses_shlex_quote(self, mock_available, mock_system, tmp_path):
        """On Unix, sentinel paths use shlex.quote() (single-quote style)."""
        inject_auto_start_task(str(tmp_path), ["copilot", "-i", "test"])

        data = json.loads((tmp_path / ".vscode" / "tasks.json").read_text(encoding="utf-8"))
        shell_cmd = data["tasks"][0]["command"]
        # shlex.quote() uses single quotes; paths must NOT be double-quoted
        # (double quotes allow $VAR expansion and command substitution).
        # Find all references to the sentinel — they should be single-quoted
        assert f"'{tmp_path}" in shell_cmd
        # Specifically: must NOT have double-quoted sentinel paths
        assert f'"{tmp_path}' not in shell_cmd

    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system", return_value="Linux")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_unix_cleanup_is_non_fatal(self, mock_available, mock_system, tmp_path):
        """On Unix, cleanup failure does not affect the task's exit code."""
        inject_auto_start_task(str(tmp_path), ["copilot", "-i", "test"])

        data = json.loads((tmp_path / ".vscode" / "tasks.json").read_text(encoding="utf-8"))
        shell_cmd = data["tasks"][0]["command"]
        # Cleanup is conditional on success and non-fatal (|| true)
        assert "|| true" in shell_cmd
        assert "if [ $agdt_exit -eq 0 ]" in shell_cmd

    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system", return_value="Linux")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_unix_exits_with_command_exit_code(self, mock_available, mock_system, tmp_path):
        """On Unix, the task exits with the Copilot command's captured exit code."""
        inject_auto_start_task(str(tmp_path), ["copilot", "-i", "test"])

        data = json.loads((tmp_path / ".vscode" / "tasks.json").read_text(encoding="utf-8"))
        shell_cmd = data["tasks"][0]["command"]
        # The final statement must be 'exit $agdt_exit'
        assert shell_cmd.rstrip().endswith("exit $agdt_exit")

    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system", return_value="Windows")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_windows_cleanup_is_non_fatal(self, mock_available, mock_system, tmp_path):
        """On Windows, cleanup failure does not affect the task's exit code."""
        inject_auto_start_task(str(tmp_path), ["copilot", "-i", "test"])

        data = json.loads((tmp_path / ".vscode" / "tasks.json").read_text(encoding="utf-8"))
        shell_cmd = data["tasks"][0]["command"]
        # Cleanup is conditional on success and non-fatal (try/catch)
        assert "if ($agdtExit -eq 0)" in shell_cmd
        assert "try {" in shell_cmd
        assert "} catch {}" in shell_cmd

    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system", return_value="Windows")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    def test_windows_exits_with_command_exit_code(self, mock_available, mock_system, tmp_path):
        """On Windows, the task exits with the Copilot command's captured exit code."""
        inject_auto_start_task(str(tmp_path), ["copilot", "-i", "test"])

        data = json.loads((tmp_path / ".vscode" / "tasks.json").read_text(encoding="utf-8"))
        shell_cmd = data["tasks"][0]["command"]
        # The final statement must be 'exit $agdtExit'
        assert shell_cmd.rstrip().endswith("exit $agdtExit")
