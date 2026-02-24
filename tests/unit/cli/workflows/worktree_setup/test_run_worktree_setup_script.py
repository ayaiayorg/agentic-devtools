"""Tests for run_worktree_setup_script."""

import sys
from unittest.mock import MagicMock, patch

from agentic_devtools.cli.workflows.worktree_setup import run_worktree_setup_script


class TestRunWorktreeSetupScript:
    """Tests for run_worktree_setup_script function."""

    def test_no_op_when_script_absent(self, tmp_path):
        """Test that the function does nothing when the setup script is missing."""
        with patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run") as mock_run:
            run_worktree_setup_script(str(tmp_path))

        mock_run.assert_not_called()

    def test_executes_script_when_present(self, tmp_path):
        """Test that the script is executed when it exists."""
        script_dir = tmp_path / ".agdt"
        script_dir.mkdir()
        script = script_dir / "agentic-devtools-worktree-setup.py"
        script.write_text("print('setup')", encoding="utf-8")

        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch(
            "agentic_devtools.cli.workflows.worktree_setup.subprocess.run", return_value=mock_result
        ) as mock_run:
            run_worktree_setup_script(str(tmp_path))

        mock_run.assert_called_once_with(
            [sys.executable, str(script), str(tmp_path)],
            cwd=str(tmp_path),
            check=False,
        )

    def test_prints_success_message_on_zero_exit(self, tmp_path, capsys):
        """Test that a success message is printed when the script exits cleanly."""
        script_dir = tmp_path / ".agdt"
        script_dir.mkdir()
        (script_dir / "agentic-devtools-worktree-setup.py").write_text("", encoding="utf-8")

        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run", return_value=mock_result):
            run_worktree_setup_script(str(tmp_path))

        captured = capsys.readouterr()
        assert "completed successfully" in captured.out

    def test_warns_on_nonzero_exit(self, tmp_path, capsys):
        """Test that a warning is printed when the script exits with a non-zero code."""
        script_dir = tmp_path / ".agdt"
        script_dir.mkdir()
        (script_dir / "agentic-devtools-worktree-setup.py").write_text("", encoding="utf-8")

        mock_result = MagicMock()
        mock_result.returncode = 1

        with patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run", return_value=mock_result):
            run_worktree_setup_script(str(tmp_path))

        captured = capsys.readouterr()
        assert "Warning" in captured.err
        assert "1" in captured.err

    def test_warns_on_os_error(self, tmp_path, capsys):
        """Test that an OSError during script execution is reported as a warning."""
        script_dir = tmp_path / ".agdt"
        script_dir.mkdir()
        (script_dir / "agentic-devtools-worktree-setup.py").write_text("", encoding="utf-8")

        with patch(
            "agentic_devtools.cli.workflows.worktree_setup.subprocess.run",
            side_effect=OSError("permission denied"),
        ):
            run_worktree_setup_script(str(tmp_path))

        captured = capsys.readouterr()
        assert "Warning" in captured.err

    def test_warns_on_file_not_found_error(self, tmp_path, capsys):
        """Test that a FileNotFoundError during script execution is reported as a warning."""
        script_dir = tmp_path / ".agdt"
        script_dir.mkdir()
        (script_dir / "agentic-devtools-worktree-setup.py").write_text("", encoding="utf-8")

        with patch(
            "agentic_devtools.cli.workflows.worktree_setup.subprocess.run",
            side_effect=FileNotFoundError("python not found"),
        ):
            run_worktree_setup_script(str(tmp_path))

        captured = capsys.readouterr()
        assert "Warning" in captured.err

    def test_prints_script_path_before_running(self, tmp_path, capsys):
        """Test that the script path is printed before execution."""
        script_dir = tmp_path / ".agdt"
        script_dir.mkdir()
        script = script_dir / "agentic-devtools-worktree-setup.py"
        script.write_text("", encoding="utf-8")

        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run", return_value=mock_result):
            run_worktree_setup_script(str(tmp_path))

        captured = capsys.readouterr()
        assert str(script) in captured.out
