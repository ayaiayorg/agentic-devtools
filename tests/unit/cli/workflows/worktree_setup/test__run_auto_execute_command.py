"""Tests for RunAutoExecuteCommand."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.workflows.worktree_setup import (
    _run_auto_execute_command,
)


def _make_mock_process(stdout_lines=None, returncode=0):
    """Create a mock Popen process with iterable stdout."""
    mock_process = MagicMock()
    mock_stdout = MagicMock()
    mock_stdout.__iter__ = MagicMock(return_value=iter(stdout_lines) if stdout_lines else iter([]))
    mock_process.stdout = mock_stdout
    mock_process.wait.return_value = None
    mock_process.returncode = returncode
    mock_process.kill = MagicMock()
    mock_process.poll.return_value = returncode
    return mock_process


def _invoke_callback_immediately(timeout, callback):
    """Timer side_effect that fires the callback synchronously on construction."""
    timer = MagicMock()
    callback()
    return timer


class TestRunAutoExecuteCommand:
    """Tests for _run_auto_execute_command function."""

    @pytest.fixture(autouse=True)
    def _patch_timer(self):
        """Patch threading.Timer to avoid spawning real timer threads."""
        with patch("threading.Timer") as mock_timer_cls:
            self.mock_timer_cls = mock_timer_cls
            yield

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    def test_returns_zero_on_success(self, mock_popen, capsys, tmp_path):
        """Test that exit code 0 is returned on success."""
        mock_process = _make_mock_process(["output text\n"])
        mock_popen.return_value = mock_process
        worktree = str(tmp_path)

        result = _run_auto_execute_command(["echo", "hello"], worktree, 300)

        assert result == 0
        mock_popen.assert_called_once()
        call_kwargs = mock_popen.call_args[1]
        assert mock_popen.call_args[0][0] == ["echo", "hello"]
        assert call_kwargs["cwd"] == worktree
        assert call_kwargs["stdout"] == subprocess.PIPE
        assert call_kwargs["stderr"] == subprocess.STDOUT
        assert call_kwargs["text"] is True
        assert call_kwargs["encoding"] == "utf-8"
        assert call_kwargs["errors"] == "replace"
        assert call_kwargs["bufsize"] == 1
        assert call_kwargs["shell"] is False
        assert "env" in call_kwargs
        mock_process.wait.assert_called_once()

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    def test_sets_state_dir_env_var(self, mock_popen, tmp_path):
        """Test fallback to _unscoped when no bootstrap file exists."""
        mock_popen.return_value = _make_mock_process()
        worktree = tmp_path / "my-worktree"
        worktree.mkdir()

        _run_auto_execute_command(["echo", "hi"], str(worktree), 60)

        call_kwargs = mock_popen.call_args[1]
        env = call_kwargs["env"]
        expected_state_dir = str(worktree / ".agdt" / "workflows" / "_unscoped")
        assert env.get("AGENTIC_DEVTOOLS_STATE_DIR") == expected_state_dir
        # .agdt/workflows/_unscoped directory must have been created
        assert (worktree / ".agdt" / "workflows" / "_unscoped").is_dir()

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    def test_state_dir_env_var_overrides_inherited(self, mock_popen, tmp_path, monkeypatch):
        """Test that the worktree state dir overrides any inherited AGENTIC_DEVTOOLS_STATE_DIR."""
        mock_popen.return_value = _make_mock_process()
        monkeypatch.setenv("AGENTIC_DEVTOOLS_STATE_DIR", "/some/other/path")
        worktree = tmp_path / "wt"
        worktree.mkdir()

        _run_auto_execute_command(["echo", "hi"], str(worktree), 60)

        call_kwargs = mock_popen.call_args[1]
        env = call_kwargs["env"]
        # No bootstrap file → falls back to _unscoped
        assert env["AGENTIC_DEVTOOLS_STATE_DIR"] == str(worktree / ".agdt" / "workflows" / "_unscoped")

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    def test_prints_stdout_on_success(self, mock_popen, capsys):
        """Test that stdout is printed when command succeeds."""
        mock_popen.return_value = _make_mock_process(["hello world\n"])

        _run_auto_execute_command(["echo", "hello world"], "/some/worktree", 300)

        captured = capsys.readouterr()
        assert "hello world" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    def test_returns_nonzero_on_failure_and_logs_warning(self, mock_popen, capsys):
        """Test that non-zero exit code is returned and warning is logged."""
        mock_popen.return_value = _make_mock_process(["error message\n"], returncode=1)

        result = _run_auto_execute_command(["false"], "/some/worktree", 300)

        assert result == 1
        captured = capsys.readouterr()
        assert "WARNING" in captured.out
        assert "1" in captured.out
        assert "error message" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    def test_returns_minus_one_on_timeout(self, mock_popen, capsys):
        """Test that -1 is returned when command times out."""
        mock_process = _make_mock_process()
        mock_process.poll.return_value = None  # process still running when timer fires
        mock_popen.return_value = mock_process

        self.mock_timer_cls.side_effect = _invoke_callback_immediately

        result = _run_auto_execute_command(["sleep", "999"], "/some/worktree", 10)

        assert result == -1
        mock_process.kill.assert_called_once()
        captured = capsys.readouterr()
        assert "WARNING" in captured.out
        assert "timed out" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    def test_returns_minus_one_on_file_not_found(self, mock_popen, capsys):
        """Test that -1 is returned when the command executable is not found."""
        mock_popen.side_effect = FileNotFoundError("No such file or directory")

        result = _run_auto_execute_command(["nonexistent-cmd"], "/some/worktree", 300)

        assert result == -1
        captured = capsys.readouterr()
        assert "WARNING" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    def test_returns_minus_one_on_os_error(self, mock_popen, capsys):
        """Test that -1 is returned on generic OSError."""
        mock_popen.side_effect = OSError("Permission denied")

        result = _run_auto_execute_command(["cmd"], "/some/worktree", 300)

        assert result == -1
        captured = capsys.readouterr()
        assert "WARNING" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    def test_logs_command_before_execution(self, mock_popen, capsys):
        """Test that the command is logged before execution."""
        mock_popen.return_value = _make_mock_process()

        _run_auto_execute_command(["agdt-initiate-review", "--pr-id", "123"], "/worktree", 60)

        captured = capsys.readouterr()
        assert "agdt-initiate-review --pr-id 123" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    def test_uses_custom_timeout(self, mock_popen, capsys):
        """Test that the custom timeout is passed to threading.Timer."""
        mock_popen.return_value = _make_mock_process()
        mock_timer = MagicMock()
        self.mock_timer_cls.return_value = mock_timer

        _run_auto_execute_command(["cmd"], "/worktree", 60)

        self.mock_timer_cls.assert_called_once()
        assert self.mock_timer_cls.call_args[0][0] == 60

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    def test_warns_when_state_dir_creation_fails(self, mock_popen, capsys, tmp_path):
        """Test that a warning is printed when state directory creation fails."""
        mock_popen.return_value = _make_mock_process()
        worktree = tmp_path / "wt"
        worktree.mkdir()

        # Patch only mkdir to simulate a permission error on the state directory
        original_mkdir = Path.mkdir

        def failing_mkdir(self_path, *args, **kwargs):
            # Only fail the specific .agdt/workflows state dir mkdir, not
            # unrelated temp-directory creations that happen to contain
            # "workflows" in the path.
            parts = self_path.parts
            if ".agdt" in parts and "workflows" in parts:
                raise OSError("Permission denied")
            return original_mkdir(self_path, *args, **kwargs)

        with patch.object(Path, "mkdir", failing_mkdir):
            _run_auto_execute_command(["cmd"], str(worktree), 60)

        captured = capsys.readouterr()
        assert "WARNING" in captured.out
        assert "Permission denied" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    def test_uses_scoped_state_dir_when_identity_json_exists(self, mock_popen, tmp_path):
        """Test that AGENTIC_DEVTOOLS_STATE_DIR uses identity/worktree_key when identity.json exists."""
        mock_popen.return_value = _make_mock_process()
        worktree = tmp_path / "my-worktree"
        worktree.mkdir()
        agdt_dir = worktree / ".agdt"
        agdt_dir.mkdir(parents=True)
        # New-style: identity in identity.json, worktree_key in runtime-bootstrap.json
        (agdt_dir / "identity.json").write_text('{"identity": "ama", "email": "a@b.com"}')
        (agdt_dir / "runtime-bootstrap.json").write_text('{"worktree_key": "PR123"}')

        _run_auto_execute_command(["echo", "hi"], str(worktree), 60)

        call_kwargs = mock_popen.call_args[1]
        env = call_kwargs["env"]
        expected = str(worktree / ".agdt" / "workflows" / "ama" / "PR123")
        assert env.get("AGENTIC_DEVTOOLS_STATE_DIR") == expected

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    def test_uses_scoped_state_dir_when_bootstrap_has_identity(self, mock_popen, tmp_path):
        """Test legacy fallback: identity/worktree_key both in runtime-bootstrap.json."""
        mock_popen.return_value = _make_mock_process()
        worktree = tmp_path / "my-worktree"
        worktree.mkdir()
        agdt_dir = worktree / ".agdt"
        agdt_dir.mkdir(parents=True)
        # Legacy format: identity stored in bootstrap (no identity.json)
        bootstrap = agdt_dir / "runtime-bootstrap.json"
        bootstrap.write_text('{"identity": "ama", "worktree_key": "PR123"}')

        _run_auto_execute_command(["echo", "hi"], str(worktree), 60)

        call_kwargs = mock_popen.call_args[1]
        env = call_kwargs["env"]
        expected = str(worktree / ".agdt" / "workflows" / "ama" / "PR123")
        assert env.get("AGENTIC_DEVTOOLS_STATE_DIR") == expected

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    def test_identity_json_takes_precedence_over_bootstrap_identity(self, mock_popen, tmp_path):
        """Test that identity.json identity overrides legacy identity in runtime-bootstrap.json."""
        mock_popen.return_value = _make_mock_process()
        worktree = tmp_path / "wt"
        worktree.mkdir()
        agdt_dir = worktree / ".agdt"
        agdt_dir.mkdir(parents=True)
        # identity.json has "new" identity; bootstrap has stale "old" identity
        (agdt_dir / "identity.json").write_text('{"identity": "new", "email": "n@b.com"}')
        (agdt_dir / "runtime-bootstrap.json").write_text('{"identity": "old", "worktree_key": "PR999"}')

        _run_auto_execute_command(["echo", "hi"], str(worktree), 60)

        call_kwargs = mock_popen.call_args[1]
        env = call_kwargs["env"]
        # identity.json wins → "new" is used, not "old"
        expected = str(worktree / ".agdt" / "workflows" / "new" / "PR999")
        assert env.get("AGENTIC_DEVTOOLS_STATE_DIR") == expected

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    def test_falls_back_to_unscoped_when_bootstrap_missing_identity(self, mock_popen, capsys, tmp_path):
        """Test silent fallback to _unscoped when bootstrap has worktree_key but no identity."""
        mock_popen.return_value = _make_mock_process()
        worktree = tmp_path / "wt"
        worktree.mkdir()
        agdt_dir = worktree / ".agdt"
        agdt_dir.mkdir(parents=True)
        bootstrap = agdt_dir / "runtime-bootstrap.json"
        bootstrap.write_text('{"worktree_key": "PR123"}')

        _run_auto_execute_command(["echo", "hi"], str(worktree), 60)

        call_kwargs = mock_popen.call_args[1]
        env = call_kwargs["env"]
        assert "_unscoped" in env.get("AGENTIC_DEVTOOLS_STATE_DIR", "")
        # Incomplete bootstrap (only one of identity/worktree_key) should NOT
        # produce an "unsafe bootstrap" warning — that is reserved for the case
        # where both are present but fail safety validation.
        captured = capsys.readouterr()
        assert "unsafe bootstrap" not in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    def test_falls_back_to_unscoped_when_bootstrap_malformed(self, mock_popen, tmp_path):
        """Test fallback to _unscoped when bootstrap file contains invalid JSON."""
        mock_popen.return_value = _make_mock_process()
        worktree = tmp_path / "wt"
        worktree.mkdir()
        agdt_dir = worktree / ".agdt"
        agdt_dir.mkdir(parents=True)
        bootstrap = agdt_dir / "runtime-bootstrap.json"
        bootstrap.write_text("NOT VALID JSON{{{")

        _run_auto_execute_command(["echo", "hi"], str(worktree), 60)

        call_kwargs = mock_popen.call_args[1]
        env = call_kwargs["env"]
        assert "_unscoped" in env.get("AGENTIC_DEVTOOLS_STATE_DIR", "")

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    def test_falls_back_to_unscoped_when_identity_is_whitespace(self, mock_popen, tmp_path):
        """Test fallback to _unscoped when bootstrap identity is whitespace-only."""
        mock_popen.return_value = _make_mock_process()
        worktree = tmp_path / "wt"
        worktree.mkdir()
        agdt_dir = worktree / ".agdt"
        agdt_dir.mkdir(parents=True)
        bootstrap = agdt_dir / "runtime-bootstrap.json"
        bootstrap.write_text('{"identity": "  ", "worktree_key": "PR123"}')

        _run_auto_execute_command(["echo", "hi"], str(worktree), 60)

        call_kwargs = mock_popen.call_args[1]
        env = call_kwargs["env"]
        assert "_unscoped" in env.get("AGENTIC_DEVTOOLS_STATE_DIR", "")

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    def test_falls_back_to_unscoped_when_identity_is_non_string(self, mock_popen, tmp_path):
        """Test fallback to _unscoped when bootstrap identity is a non-string value."""
        mock_popen.return_value = _make_mock_process()
        worktree = tmp_path / "wt"
        worktree.mkdir()
        agdt_dir = worktree / ".agdt"
        agdt_dir.mkdir(parents=True)
        bootstrap = agdt_dir / "runtime-bootstrap.json"
        bootstrap.write_text('{"identity": 42, "worktree_key": "PR123"}')

        _run_auto_execute_command(["echo", "hi"], str(worktree), 60)

        call_kwargs = mock_popen.call_args[1]
        env = call_kwargs["env"]
        assert "_unscoped" in env.get("AGENTIC_DEVTOOLS_STATE_DIR", "")

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    def test_falls_back_to_unscoped_when_identity_has_path_separator(self, mock_popen, capsys, tmp_path):
        """Test fallback to _unscoped when identity contains a path separator."""
        mock_popen.return_value = _make_mock_process()
        worktree = tmp_path / "wt"
        worktree.mkdir()
        agdt_dir = worktree / ".agdt"
        agdt_dir.mkdir(parents=True)
        bootstrap = agdt_dir / "runtime-bootstrap.json"
        bootstrap.write_text('{"identity": "../../etc", "worktree_key": "PR123"}')

        _run_auto_execute_command(["echo", "hi"], str(worktree), 60)

        call_kwargs = mock_popen.call_args[1]
        env = call_kwargs["env"]
        assert "_unscoped" in env.get("AGENTIC_DEVTOOLS_STATE_DIR", "")
        captured = capsys.readouterr()
        assert "unsafe bootstrap" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    def test_falls_back_to_unscoped_when_worktree_key_has_dotdot(self, mock_popen, capsys, tmp_path):
        """Test fallback to _unscoped when worktree_key contains '..'."""
        mock_popen.return_value = _make_mock_process()
        worktree = tmp_path / "wt"
        worktree.mkdir()
        agdt_dir = worktree / ".agdt"
        agdt_dir.mkdir(parents=True)
        bootstrap = agdt_dir / "runtime-bootstrap.json"
        bootstrap.write_text('{"identity": "ama", "worktree_key": ".."}')

        _run_auto_execute_command(["echo", "hi"], str(worktree), 60)

        call_kwargs = mock_popen.call_args[1]
        env = call_kwargs["env"]
        assert "_unscoped" in env.get("AGENTIC_DEVTOOLS_STATE_DIR", "")
        captured = capsys.readouterr()
        assert "unsafe bootstrap" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    def test_falls_back_to_unscoped_when_identity_has_backslash(self, mock_popen, capsys, tmp_path):
        """Test fallback to _unscoped when identity contains a backslash."""
        mock_popen.return_value = _make_mock_process()
        worktree = tmp_path / "wt"
        worktree.mkdir()
        agdt_dir = worktree / ".agdt"
        agdt_dir.mkdir(parents=True)
        bootstrap = agdt_dir / "runtime-bootstrap.json"
        bootstrap.write_text('{"identity": "foo\\\\bar", "worktree_key": "PR1"}')

        _run_auto_execute_command(["echo", "hi"], str(worktree), 60)

        call_kwargs = mock_popen.call_args[1]
        env = call_kwargs["env"]
        assert "_unscoped" in env.get("AGENTIC_DEVTOOLS_STATE_DIR", "")
        captured = capsys.readouterr()
        assert "unsafe bootstrap" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    def test_falls_back_to_unscoped_when_identity_has_drive_letter(self, mock_popen, capsys, tmp_path):
        """Test fallback to _unscoped when identity contains a Windows drive letter (e.g. C:)."""
        mock_popen.return_value = _make_mock_process()
        worktree = tmp_path / "wt"
        worktree.mkdir()
        agdt_dir = worktree / ".agdt"
        agdt_dir.mkdir(parents=True)
        bootstrap = agdt_dir / "runtime-bootstrap.json"
        bootstrap.write_text('{"identity": "D:", "worktree_key": "PR1"}')

        _run_auto_execute_command(["echo", "hi"], str(worktree), 60)

        call_kwargs = mock_popen.call_args[1]
        env = call_kwargs["env"]
        assert "_unscoped" in env.get("AGENTIC_DEVTOOLS_STATE_DIR", "")
        captured = capsys.readouterr()
        assert "unsafe bootstrap" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    def test_falls_back_gracefully_when_identity_json_malformed(self, mock_popen, tmp_path):
        """Test fallback to legacy bootstrap when identity.json contains invalid JSON."""
        mock_popen.return_value = _make_mock_process()
        worktree = tmp_path / "wt"
        worktree.mkdir()
        agdt_dir = worktree / ".agdt"
        agdt_dir.mkdir(parents=True)
        # Malformed identity.json → falls back to legacy bootstrap
        (agdt_dir / "identity.json").write_text("NOT VALID JSON{{{")
        (agdt_dir / "runtime-bootstrap.json").write_text('{"identity": "ama", "worktree_key": "PR123"}')

        _run_auto_execute_command(["echo", "hi"], str(worktree), 60)

        call_kwargs = mock_popen.call_args[1]
        env = call_kwargs["env"]
        # Malformed identity.json → legacy fallback resolves identity from bootstrap
        expected = str(worktree / ".agdt" / "workflows" / "ama" / "PR123")
        assert env.get("AGENTIC_DEVTOOLS_STATE_DIR") == expected

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    def test_streams_output_line_by_line(self, mock_popen, capsys):
        """Test that each line from process stdout is individually written to sys.stdout."""
        mock_popen.return_value = _make_mock_process(["line one\n", "line two\n", "line three\n"])

        _run_auto_execute_command(["cmd"], "/some/worktree", 300)

        captured = capsys.readouterr()
        assert "line one\n" in captured.out
        assert "line two\n" in captured.out
        assert "line three\n" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    def test_timeout_kills_process_and_returns_minus_one(self, mock_popen, capsys):
        """Test that when the timer fires while process is running, kill() is called and returns -1."""
        mock_process = _make_mock_process()
        mock_process.poll.return_value = None  # process still running
        mock_popen.return_value = mock_process

        self.mock_timer_cls.side_effect = _invoke_callback_immediately

        result = _run_auto_execute_command(["long-cmd"], "/some/worktree", 30)

        assert result == -1
        mock_process.kill.assert_called_once()
        captured = capsys.readouterr()
        assert "timed out" in captured.out
        assert "30" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    def test_timer_noop_when_process_already_exited(self, mock_popen, capsys):
        """Test that timer callback is a no-op when process already exited."""
        mock_process = _make_mock_process()
        mock_process.poll.return_value = 0  # process already exited
        mock_popen.return_value = mock_process

        self.mock_timer_cls.side_effect = _invoke_callback_immediately

        result = _run_auto_execute_command(["cmd"], "/some/worktree", 60)

        assert result == 0
        mock_process.kill.assert_not_called()
        captured = capsys.readouterr()
        assert "timed out" not in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    def test_timeout_race_kill_raises_process_lookup_error(self, mock_popen, capsys):
        """Test that ProcessLookupError from kill() during timeout is handled gracefully."""
        mock_process = _make_mock_process()
        mock_process.poll.return_value = None  # process appears running
        mock_process.kill.side_effect = ProcessLookupError  # but exits before kill()
        mock_popen.return_value = mock_process

        self.mock_timer_cls.side_effect = _invoke_callback_immediately

        result = _run_auto_execute_command(["long-cmd"], "/some/worktree", 30)

        assert result == -1
        mock_process.kill.assert_called_once()
        captured = capsys.readouterr()
        assert "timed out" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    def test_identity_cache_not_found_reads_bootstrap_only(self, mock_popen, tmp_path):
        """When identity.json does not exist but bootstrap has identity, uses bootstrap identity."""
        mock_popen.return_value = _make_mock_process()
        worktree = tmp_path / "wt"
        worktree.mkdir()
        agdt_dir = worktree / ".agdt"
        agdt_dir.mkdir(parents=True)
        # No identity.json — identity_cache_path.is_file() returns False
        (agdt_dir / "runtime-bootstrap.json").write_text('{"identity": "bootstrapped", "worktree_key": "WK1"}')

        _run_auto_execute_command(["echo", "hi"], str(worktree), 60)

        call_kwargs = mock_popen.call_args[1]
        env = call_kwargs["env"]
        expected = str(worktree / ".agdt" / "workflows" / "bootstrapped" / "WK1")
        assert env.get("AGENTIC_DEVTOOLS_STATE_DIR") == expected

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    def test_unsafe_identity_with_both_values_prints_warning(self, mock_popen, capsys, tmp_path):
        """When both identity and worktree_key present but identity is unsafe, prints WARNING."""
        mock_popen.return_value = _make_mock_process()
        worktree = tmp_path / "wt"
        worktree.mkdir()
        agdt_dir = worktree / ".agdt"
        agdt_dir.mkdir(parents=True)
        (agdt_dir / "runtime-bootstrap.json").write_text('{"identity": "../escape", "worktree_key": "PR1"}')

        _run_auto_execute_command(["echo", "hi"], str(worktree), 60)

        call_kwargs = mock_popen.call_args[1]
        env = call_kwargs["env"]
        assert "_unscoped" in env.get("AGENTIC_DEVTOOLS_STATE_DIR", "")
        captured = capsys.readouterr()
        assert "unsafe bootstrap" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    def test_nonzero_exit_code_prints_warning_and_returns_code(self, mock_popen, capsys):
        """Non-zero exit code prints WARNING with exit code."""
        mock_popen.return_value = _make_mock_process(["output\n"], returncode=42)

        result = _run_auto_execute_command(["failing-cmd"], "/some/worktree", 300)

        assert result == 42
        captured = capsys.readouterr()
        assert "WARNING" in captured.out
        assert "42" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    def test_timeout_prints_warning_and_returns_minus_one(self, mock_popen, capsys):
        """Timeout prints WARNING with timeout value and returns -1."""
        mock_process = _make_mock_process()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        self.mock_timer_cls.side_effect = _invoke_callback_immediately

        result = _run_auto_execute_command(["slow-cmd"], "/some/worktree", 45)

        assert result == -1
        captured = capsys.readouterr()
        assert "timed out" in captured.out
        assert "45" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    def test_identity_json_non_dict_falls_back_to_bootstrap(self, mock_popen, tmp_path):
        """When identity.json contains non-dict JSON, falls back to bootstrap.

        Covers branch 2148->2154.
        """
        mock_popen.return_value = _make_mock_process()
        worktree = tmp_path / "wt"
        worktree.mkdir()
        agdt_dir = worktree / ".agdt"
        agdt_dir.mkdir(parents=True)
        # identity.json with non-dict content (a list)
        (agdt_dir / "identity.json").write_text('["not", "a", "dict"]')
        (agdt_dir / "runtime-bootstrap.json").write_text('{"identity": "user1", "worktree_key": "WK1"}')

        _run_auto_execute_command(["echo", "hi"], str(worktree), 60)

        call_kwargs = mock_popen.call_args[1]
        env = call_kwargs["env"]
        expected = str(worktree / ".agdt" / "workflows" / "user1" / "WK1")
        assert env.get("AGENTIC_DEVTOOLS_STATE_DIR") == expected

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    def test_bootstrap_non_dict_falls_back_to_unscoped(self, mock_popen, tmp_path):
        """When runtime-bootstrap.json contains non-dict JSON, falls back to _unscoped.

        Covers branch 2158->2171.
        """
        mock_popen.return_value = _make_mock_process()
        worktree = tmp_path / "wt"
        worktree.mkdir()
        agdt_dir = worktree / ".agdt"
        agdt_dir.mkdir(parents=True)
        # bootstrap with non-dict content (a string)
        (agdt_dir / "runtime-bootstrap.json").write_text('"just a string"')

        _run_auto_execute_command(["echo", "hi"], str(worktree), 60)

        call_kwargs = mock_popen.call_args[1]
        env = call_kwargs["env"]
        assert "_unscoped" in env.get("AGENTIC_DEVTOOLS_STATE_DIR", "")

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    def test_handles_process_with_none_stdout(self, mock_popen, capsys):
        """When process.stdout is None, the function still completes.

        Covers branches 2221->2225 and 2228->2231.
        """
        mock_process = _make_mock_process()
        mock_process.stdout = None
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        result = _run_auto_execute_command(["echo", "hi"], "/some/worktree", 300)

        assert result == 0


class TestRunAutoExecuteCommandPinFile:
    """Tests for pin file writing in _run_auto_execute_command."""

    @pytest.fixture(autouse=True)
    def _patch_timer(self):
        """Patch threading.Timer to avoid spawning real timer threads."""
        with patch("threading.Timer") as mock_timer_cls:
            self.mock_timer_cls = mock_timer_cls
            yield

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    def test_pin_file_written_to_target_worktree(self, mock_popen, tmp_path):
        """When workflow is provided, pin file is written to target worktree's .agdt/ dir."""
        mock_popen.return_value = _make_mock_process()
        worktree = tmp_path / "my-worktree"
        worktree.mkdir()
        (worktree / ".git").write_text("gitdir: /tmp/worktrees/my-worktree", encoding="utf-8")
        agdt_dir = worktree / ".agdt"
        agdt_dir.mkdir(parents=True)
        (agdt_dir / "identity.json").write_text('{"identity": "ama", "email": "a@b.com"}')
        (agdt_dir / "runtime-bootstrap.json").write_text('{"worktree_key": "PR123"}')

        _run_auto_execute_command(["echo", "hi"], str(worktree), 60, workflow="pull-request-review")

        import json

        from agentic_devtools.state import PIN_FILENAME

        pin_path = agdt_dir / PIN_FILENAME
        assert pin_path.exists()
        data = json.loads(pin_path.read_text(encoding="utf-8"))
        expected_state_dir = str(worktree / ".agdt" / "workflows" / "ama" / "PR123")
        assert data["state_dir"] == str(Path(expected_state_dir).resolve())
        assert data["workflow"] == "pull-request-review"

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    def test_pin_file_content_matches_resolved_state_dir(self, mock_popen, capsys, tmp_path):
        """Pin file state_dir matches the AGENTIC_DEVTOOLS_STATE_DIR env var value."""
        mock_popen.return_value = _make_mock_process()
        worktree = tmp_path / "wt"
        worktree.mkdir()
        (worktree / ".git").write_text("gitdir: /tmp/worktrees/wt", encoding="utf-8")
        agdt_dir = worktree / ".agdt"
        agdt_dir.mkdir(parents=True)
        (agdt_dir / "identity.json").write_text('{"identity": "user1", "email": "u@b.com"}')
        (agdt_dir / "runtime-bootstrap.json").write_text('{"worktree_key": "ISSUE-456"}')

        _run_auto_execute_command(["echo", "hi"], str(worktree), 60, workflow="work-on-jira-issue")

        import json

        from agentic_devtools.state import PIN_FILENAME

        pin_path = agdt_dir / PIN_FILENAME
        data = json.loads(pin_path.read_text(encoding="utf-8"))
        # Verify it matches what was passed as env var to subprocess
        call_kwargs = mock_popen.call_args[1]
        env_state_dir = call_kwargs["env"]["AGENTIC_DEVTOOLS_STATE_DIR"]
        assert data["state_dir"] == str(Path(env_state_dir).resolve())

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    def test_pin_file_not_written_when_workflow_is_none(self, mock_popen, tmp_path):
        """When workflow=None, no pin file is written (backward compat)."""
        mock_popen.return_value = _make_mock_process()
        worktree = tmp_path / "wt"
        worktree.mkdir()
        agdt_dir = worktree / ".agdt"
        agdt_dir.mkdir(parents=True)
        (agdt_dir / "identity.json").write_text('{"identity": "ama", "email": "a@b.com"}')
        (agdt_dir / "runtime-bootstrap.json").write_text('{"worktree_key": "PR123"}')

        _run_auto_execute_command(["echo", "hi"], str(worktree), 60, workflow=None)

        from agentic_devtools.state import PIN_FILENAME

        pin_path = agdt_dir / PIN_FILENAME
        assert not pin_path.exists()

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    def test_subprocess_still_runs_when_pin_write_fails(self, mock_popen, capsys, tmp_path):
        """When pin file write fails, subprocess is still executed."""
        mock_popen.return_value = _make_mock_process()
        worktree = tmp_path / "wt"
        worktree.mkdir()
        agdt_dir = worktree / ".agdt"
        agdt_dir.mkdir(parents=True)
        (agdt_dir / "identity.json").write_text('{"identity": "ama", "email": "a@b.com"}')
        (agdt_dir / "runtime-bootstrap.json").write_text('{"worktree_key": "PR123"}')

        with patch(
            "agentic_devtools.state.write_pin_file",
            side_effect=OSError("disk full"),
        ):
            result = _run_auto_execute_command(["echo", "hi"], str(worktree), 60, workflow="pull-request-review")

        # Subprocess should still have been called
        mock_popen.assert_called_once()
        assert result == 0
        captured = capsys.readouterr()
        assert "Failed to write pin file" in captured.err

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    def test_no_pinned_message_when_write_pin_returns_none(self, mock_popen, capsys, tmp_path):
        """When write_pin_file returns None, 'Pinned state dir' is not printed."""
        mock_popen.return_value = _make_mock_process()
        worktree = tmp_path / "wt"
        worktree.mkdir()
        agdt_dir = worktree / ".agdt"
        agdt_dir.mkdir(parents=True)
        (agdt_dir / "identity.json").write_text('{"identity": "ama", "email": "a@b.com"}')
        (agdt_dir / "runtime-bootstrap.json").write_text('{"worktree_key": "PR123"}')

        with patch(
            "agentic_devtools.state.write_pin_file",
            return_value=None,
        ):
            _run_auto_execute_command(["echo", "hi"], str(worktree), 60, workflow="pull-request-review")

        captured = capsys.readouterr()
        assert "Pinned state dir" not in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    def test_diagnostic_log_emitted(self, mock_popen, capsys, tmp_path):
        """Diagnostic log with resolved state directory is always emitted."""
        mock_popen.return_value = _make_mock_process()
        worktree = tmp_path / "wt"
        worktree.mkdir()
        agdt_dir = worktree / ".agdt"
        agdt_dir.mkdir(parents=True)
        (agdt_dir / "identity.json").write_text('{"identity": "ama", "email": "a@b.com"}')
        (agdt_dir / "runtime-bootstrap.json").write_text('{"worktree_key": "PR999"}')

        _run_auto_execute_command(["echo", "hi"], str(worktree), 60)

        captured = capsys.readouterr()
        expected_dir = str(worktree / ".agdt" / "workflows" / "ama" / "PR999")
        assert f"Resolved state directory: {expected_dir}" in captured.out
