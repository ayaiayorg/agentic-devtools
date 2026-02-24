"""Tests for run_worktree_setup_script."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.workflows.worktree_setup import run_worktree_setup_script


class TestRunWorktreeSetupScript:
    """Tests for run_worktree_setup_script function."""

    def test_no_op_when_script_absent(self, tmp_path):
        """Test that the function does nothing when the setup script is missing."""
        with patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run") as mock_run:
            run_worktree_setup_script(str(tmp_path))

        mock_run.assert_not_called()

    def test_no_op_when_path_is_directory(self, tmp_path):
        """Test that a directory at the script path is treated as absent (no execution)."""
        script_dir = tmp_path / ".agdt"
        script_dir.mkdir()
        # Create a *directory* where the script should be
        (script_dir / "agentic-devtools-worktree-setup.py").mkdir()

        with patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run") as mock_run:
            run_worktree_setup_script(str(tmp_path))

        mock_run.assert_not_called()

    def test_no_op_when_script_not_readable(self, tmp_path):
        """Test that a non-readable script file is treated as absent (no execution)."""
        script_dir = tmp_path / ".agdt"
        script_dir.mkdir()
        script = script_dir / "agentic-devtools-worktree-setup.py"
        script.write_text("", encoding="utf-8")

        with patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run") as mock_run:
            with patch("agentic_devtools.cli.workflows.worktree_setup.os.access", return_value=False):
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
            [sys.executable, str(script.resolve()), str(tmp_path.resolve())],
            cwd=str(tmp_path.resolve()),
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
        assert str(script.resolve()) in captured.out

    def test_rejects_symlink_script(self, tmp_path, capsys):
        """Test that a symlinked setup script is refused with a warning."""
        # Create the .agdt dir and a real target file inside the worktree
        script_dir = tmp_path / ".agdt"
        script_dir.mkdir()
        real_file = tmp_path / "real_setup.py"
        real_file.write_text("print('evil')", encoding="utf-8")
        symlink = script_dir / "agentic-devtools-worktree-setup.py"
        try:
            symlink.symlink_to(real_file)
        except OSError:
            pytest.skip("Symlink creation not supported on this platform/configuration")

        with patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run") as mock_run:
            run_worktree_setup_script(str(tmp_path))

        mock_run.assert_not_called()
        captured = capsys.readouterr()
        assert "Warning" in captured.err
        assert "symlink" in captured.err

    def test_rejects_script_resolving_outside_worktree(self, tmp_path, capsys):
        """Test that a script resolving outside the worktree root is refused."""
        script_dir = tmp_path / ".agdt"
        script_dir.mkdir()
        script = script_dir / "agentic-devtools-worktree-setup.py"
        script.write_text("", encoding="utf-8")

        outside_path = tmp_path.parent / "evil.py"

        # The implementation calls Path.resolve() twice: first for worktree_root,
        # then for the script path. We use a counter so that only the second call
        # (for the script) returns an outside path; the first call returns normally.
        _real_resolve = Path.resolve
        _calls = [0]

        def _mock_resolve(self):
            _calls[0] += 1
            if _calls[0] == 1:
                return _real_resolve(self)
            return outside_path

        with patch.object(Path, "resolve", _mock_resolve):
            with patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run") as mock_run:
                run_worktree_setup_script(str(tmp_path))

        mock_run.assert_not_called()
        captured = capsys.readouterr()
        assert "Warning" in captured.err
        assert "outside worktree" in captured.err

    def test_warns_on_os_error_during_path_validation(self, tmp_path, capsys):
        """Test that an OSError during path validation is reported as a warning."""
        script_dir = tmp_path / ".agdt"
        script_dir.mkdir()
        script = script_dir / "agentic-devtools-worktree-setup.py"
        script.write_text("", encoding="utf-8")

        with patch.object(type(script), "is_symlink", side_effect=OSError("stat failed")):
            with patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run") as mock_run:
                run_worktree_setup_script(str(tmp_path))

        mock_run.assert_not_called()
        captured = capsys.readouterr()
        assert "Warning" in captured.err
        assert "validate" in captured.err
