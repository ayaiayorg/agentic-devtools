"""Tests for the testing module.

These tests test the SYNC functions (_run_tests_sync, _run_tests_quick_sync, etc.)
which do the actual work. The async wrapper functions (run_tests, run_tests_quick, etc.)
simply call run_function_in_background which spawns these sync functions in a subprocess.

Testing the async wrappers would require mocking run_function_in_background, which
is tested separately in test_background_tasks.py.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli import testing


class TestRunSubprocessWithStreaming:
    """Tests for _run_subprocess_with_streaming function."""

    def test_streams_output_to_stdout(self, tmp_path, capsys):
        """Should stream subprocess output to stdout."""
        # Create a simple script that outputs text
        script = tmp_path / "test_script.py"
        script.write_text('print("Hello from subprocess")')

        result = testing._run_subprocess_with_streaming(
            [sys.executable, str(script)],
            str(tmp_path),
        )

        captured = capsys.readouterr()
        assert "Hello from subprocess" in captured.out
        assert result == 0

    def test_returns_subprocess_exit_code(self, tmp_path):
        """Should return the subprocess exit code."""
        # Create a script that exits with code 42
        script = tmp_path / "exit_script.py"
        script.write_text("import sys; sys.exit(42)")

        result = testing._run_subprocess_with_streaming(
            [sys.executable, str(script)],
            str(tmp_path),
        )

        assert result == 42

    def test_handles_stderr_merged_to_stdout(self, tmp_path, capsys):
        """Should capture stderr in stdout stream."""
        # Create a script that writes to stderr
        script = tmp_path / "stderr_script.py"
        script.write_text('import sys; print("error message", file=sys.stderr)')

        result = testing._run_subprocess_with_streaming(
            [sys.executable, str(script)],
            str(tmp_path),
        )

        captured = capsys.readouterr()
        assert "error message" in captured.out
        assert result == 0

    def test_handles_none_stdout(self, tmp_path):
        """Should handle case where process.stdout is None gracefully."""
        from unittest.mock import MagicMock, patch

        mock_process = MagicMock()
        mock_process.stdout = None  # Simulate stdout being None
        mock_process.returncode = 0

        with patch.object(testing, "subprocess") as mock_subprocess:
            mock_subprocess.Popen.return_value = mock_process
            mock_subprocess.PIPE = -1
            mock_subprocess.STDOUT = -2

            result = testing._run_subprocess_with_streaming(
                ["some", "command"],
                str(tmp_path),
            )

            assert result == 0
            mock_process.wait.assert_called_once()
