"""Tests for RunAutoExecuteCommand."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from agentic_devtools.cli.workflows.worktree_setup import (
    _run_auto_execute_command,
)


class TestRunAutoExecuteCommand:
    """Tests for _run_auto_execute_command function."""

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_zero_on_success(self, mock_run, capsys, tmp_path):
        """Test that exit code 0 is returned on success."""
        mock_run.return_value = MagicMock(returncode=0, stdout="output text", stderr="")
        worktree = str(tmp_path)

        result = _run_auto_execute_command(["echo", "hello"], worktree, 300)

        assert result == 0
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert mock_run.call_args[0][0] == ["echo", "hello"]
        assert call_kwargs["cwd"] == worktree
        assert call_kwargs["capture_output"] is True
        assert call_kwargs["text"] is True
        assert call_kwargs["timeout"] == 300
        assert call_kwargs["shell"] is False
        assert "env" in call_kwargs

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_sets_state_dir_env_var(self, mock_run, tmp_path):
        """Test fallback to _unscoped when no bootstrap file exists."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        worktree = tmp_path / "my-worktree"
        worktree.mkdir()

        _run_auto_execute_command(["echo", "hi"], str(worktree), 60)

        call_kwargs = mock_run.call_args[1]
        env = call_kwargs["env"]
        expected_state_dir = str(worktree / ".agdt" / "workflows" / "_unscoped")
        assert env.get("AGENTIC_DEVTOOLS_STATE_DIR") == expected_state_dir
        # .agdt/workflows/_unscoped directory must have been created
        assert (worktree / ".agdt" / "workflows" / "_unscoped").is_dir()

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_state_dir_env_var_overrides_inherited(self, mock_run, tmp_path, monkeypatch):
        """Test that the worktree state dir overrides any inherited AGENTIC_DEVTOOLS_STATE_DIR."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        monkeypatch.setenv("AGENTIC_DEVTOOLS_STATE_DIR", "/some/other/path")
        worktree = tmp_path / "wt"
        worktree.mkdir()

        _run_auto_execute_command(["echo", "hi"], str(worktree), 60)

        call_kwargs = mock_run.call_args[1]
        env = call_kwargs["env"]
        # No bootstrap file → falls back to _unscoped
        assert env["AGENTIC_DEVTOOLS_STATE_DIR"] == str(worktree / ".agdt" / "workflows" / "_unscoped")

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_prints_stdout_on_success(self, mock_run, capsys):
        """Test that stdout is printed when command succeeds."""
        mock_run.return_value = MagicMock(returncode=0, stdout="hello world\n", stderr="")

        _run_auto_execute_command(["echo", "hello world"], "/some/worktree", 300)

        captured = capsys.readouterr()
        assert "hello world" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_nonzero_on_failure_and_logs_warning(self, mock_run, capsys):
        """Test that non-zero exit code is returned and warning is logged."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error message")

        result = _run_auto_execute_command(["false"], "/some/worktree", 300)

        assert result == 1
        captured = capsys.readouterr()
        assert "WARNING" in captured.out
        assert "1" in captured.out
        assert "error message" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_minus_one_on_timeout(self, mock_run, capsys):
        """Test that -1 is returned when command times out."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["cmd"], timeout=10)

        result = _run_auto_execute_command(["sleep", "999"], "/some/worktree", 10)

        assert result == -1
        captured = capsys.readouterr()
        assert "WARNING" in captured.out
        assert "timed out" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_minus_one_on_file_not_found(self, mock_run, capsys):
        """Test that -1 is returned when the command executable is not found."""
        mock_run.side_effect = FileNotFoundError("No such file or directory")

        result = _run_auto_execute_command(["nonexistent-cmd"], "/some/worktree", 300)

        assert result == -1
        captured = capsys.readouterr()
        assert "WARNING" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_minus_one_on_os_error(self, mock_run, capsys):
        """Test that -1 is returned on generic OSError."""
        mock_run.side_effect = OSError("Permission denied")

        result = _run_auto_execute_command(["cmd"], "/some/worktree", 300)

        assert result == -1
        captured = capsys.readouterr()
        assert "WARNING" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_logs_command_before_execution(self, mock_run, capsys):
        """Test that the command is logged before execution."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        _run_auto_execute_command(["agdt-initiate-review", "--pr-id", "123"], "/worktree", 60)

        captured = capsys.readouterr()
        assert "agdt-initiate-review --pr-id 123" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_uses_custom_timeout(self, mock_run, capsys):
        """Test that the custom timeout is passed to subprocess.run."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        _run_auto_execute_command(["cmd"], "/worktree", 60)

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["timeout"] == 60

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_warns_when_state_dir_creation_fails(self, mock_run, capsys, tmp_path):
        """Test that a warning is printed when state directory creation fails."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
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

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_uses_scoped_state_dir_when_bootstrap_has_identity(self, mock_run, tmp_path):
        """Test that AGENTIC_DEVTOOLS_STATE_DIR uses identity/worktree_key when bootstrap exists."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        worktree = tmp_path / "my-worktree"
        worktree.mkdir()
        agdt_dir = worktree / ".agdt"
        agdt_dir.mkdir(parents=True)
        bootstrap = agdt_dir / "runtime-bootstrap.json"
        bootstrap.write_text('{"identity": "ama", "worktree_key": "PR123"}')

        _run_auto_execute_command(["echo", "hi"], str(worktree), 60)

        call_kwargs = mock_run.call_args[1]
        env = call_kwargs["env"]
        expected = str(worktree / ".agdt" / "workflows" / "ama" / "PR123")
        assert env.get("AGENTIC_DEVTOOLS_STATE_DIR") == expected

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_falls_back_to_unscoped_when_bootstrap_missing_identity(self, mock_run, capsys, tmp_path):
        """Test silent fallback to _unscoped when bootstrap has worktree_key but no identity."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        worktree = tmp_path / "wt"
        worktree.mkdir()
        agdt_dir = worktree / ".agdt"
        agdt_dir.mkdir(parents=True)
        bootstrap = agdt_dir / "runtime-bootstrap.json"
        bootstrap.write_text('{"worktree_key": "PR123"}')

        _run_auto_execute_command(["echo", "hi"], str(worktree), 60)

        call_kwargs = mock_run.call_args[1]
        env = call_kwargs["env"]
        assert "_unscoped" in env.get("AGENTIC_DEVTOOLS_STATE_DIR", "")
        # Incomplete bootstrap (only one of identity/worktree_key) should NOT
        # produce an "unsafe bootstrap" warning — that is reserved for the case
        # where both are present but fail safety validation.
        captured = capsys.readouterr()
        assert "unsafe bootstrap" not in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_falls_back_to_unscoped_when_bootstrap_malformed(self, mock_run, tmp_path):
        """Test fallback to _unscoped when bootstrap file contains invalid JSON."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        worktree = tmp_path / "wt"
        worktree.mkdir()
        agdt_dir = worktree / ".agdt"
        agdt_dir.mkdir(parents=True)
        bootstrap = agdt_dir / "runtime-bootstrap.json"
        bootstrap.write_text("NOT VALID JSON{{{")

        _run_auto_execute_command(["echo", "hi"], str(worktree), 60)

        call_kwargs = mock_run.call_args[1]
        env = call_kwargs["env"]
        assert "_unscoped" in env.get("AGENTIC_DEVTOOLS_STATE_DIR", "")

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_falls_back_to_unscoped_when_identity_is_whitespace(self, mock_run, tmp_path):
        """Test fallback to _unscoped when bootstrap identity is whitespace-only."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        worktree = tmp_path / "wt"
        worktree.mkdir()
        agdt_dir = worktree / ".agdt"
        agdt_dir.mkdir(parents=True)
        bootstrap = agdt_dir / "runtime-bootstrap.json"
        bootstrap.write_text('{"identity": "  ", "worktree_key": "PR123"}')

        _run_auto_execute_command(["echo", "hi"], str(worktree), 60)

        call_kwargs = mock_run.call_args[1]
        env = call_kwargs["env"]
        assert "_unscoped" in env.get("AGENTIC_DEVTOOLS_STATE_DIR", "")

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_falls_back_to_unscoped_when_identity_is_non_string(self, mock_run, tmp_path):
        """Test fallback to _unscoped when bootstrap identity is a non-string value."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        worktree = tmp_path / "wt"
        worktree.mkdir()
        agdt_dir = worktree / ".agdt"
        agdt_dir.mkdir(parents=True)
        bootstrap = agdt_dir / "runtime-bootstrap.json"
        bootstrap.write_text('{"identity": 42, "worktree_key": "PR123"}')

        _run_auto_execute_command(["echo", "hi"], str(worktree), 60)

        call_kwargs = mock_run.call_args[1]
        env = call_kwargs["env"]
        assert "_unscoped" in env.get("AGENTIC_DEVTOOLS_STATE_DIR", "")

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_falls_back_to_unscoped_when_identity_has_path_separator(self, mock_run, capsys, tmp_path):
        """Test fallback to _unscoped when identity contains a path separator."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        worktree = tmp_path / "wt"
        worktree.mkdir()
        agdt_dir = worktree / ".agdt"
        agdt_dir.mkdir(parents=True)
        bootstrap = agdt_dir / "runtime-bootstrap.json"
        bootstrap.write_text('{"identity": "../../etc", "worktree_key": "PR123"}')

        _run_auto_execute_command(["echo", "hi"], str(worktree), 60)

        call_kwargs = mock_run.call_args[1]
        env = call_kwargs["env"]
        assert "_unscoped" in env.get("AGENTIC_DEVTOOLS_STATE_DIR", "")
        captured = capsys.readouterr()
        assert "unsafe bootstrap" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_falls_back_to_unscoped_when_worktree_key_has_dotdot(self, mock_run, capsys, tmp_path):
        """Test fallback to _unscoped when worktree_key contains '..'."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        worktree = tmp_path / "wt"
        worktree.mkdir()
        agdt_dir = worktree / ".agdt"
        agdt_dir.mkdir(parents=True)
        bootstrap = agdt_dir / "runtime-bootstrap.json"
        bootstrap.write_text('{"identity": "ama", "worktree_key": ".."}')

        _run_auto_execute_command(["echo", "hi"], str(worktree), 60)

        call_kwargs = mock_run.call_args[1]
        env = call_kwargs["env"]
        assert "_unscoped" in env.get("AGENTIC_DEVTOOLS_STATE_DIR", "")
        captured = capsys.readouterr()
        assert "unsafe bootstrap" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_falls_back_to_unscoped_when_identity_has_backslash(self, mock_run, capsys, tmp_path):
        """Test fallback to _unscoped when identity contains a backslash."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        worktree = tmp_path / "wt"
        worktree.mkdir()
        agdt_dir = worktree / ".agdt"
        agdt_dir.mkdir(parents=True)
        bootstrap = agdt_dir / "runtime-bootstrap.json"
        bootstrap.write_text('{"identity": "foo\\\\bar", "worktree_key": "PR1"}')

        _run_auto_execute_command(["echo", "hi"], str(worktree), 60)

        call_kwargs = mock_run.call_args[1]
        env = call_kwargs["env"]
        assert "_unscoped" in env.get("AGENTIC_DEVTOOLS_STATE_DIR", "")
        captured = capsys.readouterr()
        assert "unsafe bootstrap" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_falls_back_to_unscoped_when_identity_has_drive_letter(self, mock_run, capsys, tmp_path):
        """Test fallback to _unscoped when identity contains a Windows drive letter (e.g. C:)."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        worktree = tmp_path / "wt"
        worktree.mkdir()
        agdt_dir = worktree / ".agdt"
        agdt_dir.mkdir(parents=True)
        bootstrap = agdt_dir / "runtime-bootstrap.json"
        bootstrap.write_text('{"identity": "D:", "worktree_key": "PR1"}')

        _run_auto_execute_command(["echo", "hi"], str(worktree), 60)

        call_kwargs = mock_run.call_args[1]
        env = call_kwargs["env"]
        assert "_unscoped" in env.get("AGENTIC_DEVTOOLS_STATE_DIR", "")
        captured = capsys.readouterr()
        assert "unsafe bootstrap" in captured.out
