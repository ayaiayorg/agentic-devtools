"""
Tests for subprocess_utils module - safe subprocess execution.
"""

import subprocess
from unittest.mock import patch

import pytest

from agdt_ai_helpers.cli.subprocess_utils import run_safe


class TestRunSafe:
    """Tests for run_safe function."""

    def test_run_safe_successful_command(self):
        """Test run_safe executes command successfully."""
        # Use python instead of echo since echo is a shell built-in on Windows
        result = run_safe(["python", "-c", "print('hello')"], capture_output=True, text=True)
        assert result.returncode == 0
        assert "hello" in result.stdout

    def test_run_safe_failed_command(self):
        """Test run_safe handles failed commands."""
        result = run_safe(["python", "-c", "exit(1)"])
        assert result.returncode == 1

    def test_run_safe_with_capture_output(self):
        """Test run_safe captures output when capture_output=True."""
        result = run_safe(["python", "-c", "print('captured')"], capture_output=True, text=True)
        assert result.returncode == 0
        assert "captured" in result.stdout

    def test_run_safe_with_text_mode(self):
        """Test run_safe uses text mode when text=True."""
        result = run_safe(["python", "-c", "print('text')"], capture_output=True, text=True)
        assert isinstance(result.stdout, str)
        assert isinstance(result.stderr, str)

    def test_run_safe_without_text_mode(self):
        """Test run_safe returns bytes when text=False."""
        result = run_safe(["python", "-c", "print('bytes')"], capture_output=True, text=False)
        assert isinstance(result.stdout, bytes)
        assert isinstance(result.stderr, bytes)

    def test_run_safe_with_kwargs(self):
        """Test run_safe passes additional kwargs to subprocess.run."""
        result = run_safe(["python", "-c", "print('test')"], capture_output=True, text=True, cwd=".")
        assert result.returncode == 0

    def test_run_safe_returns_completed_process(self):
        """Test run_safe returns a CompletedProcess instance."""
        result = run_safe(["python", "-c", "print('test')"])
        assert isinstance(result, subprocess.CompletedProcess)
        assert hasattr(result, "returncode")
        assert hasattr(result, "stdout")
        assert hasattr(result, "stderr")

    @patch("agdt_ai_helpers.cli.subprocess_utils.subprocess.run")
    def test_run_safe_handles_keyboard_interrupt(self, mock_run):
        """Test run_safe handles KeyboardInterrupt gracefully."""
        mock_run.side_effect = KeyboardInterrupt()

        result = run_safe(["python", "-c", "print('test')"], text=True)

        assert result.returncode == -1
        assert result.stdout == ""
        assert "Interrupted" in result.stderr

    @patch("agdt_ai_helpers.cli.subprocess_utils.subprocess.run")
    def test_run_safe_handles_unicode_decode_error(self, mock_run):
        """Test run_safe handles UnicodeDecodeError gracefully."""
        mock_run.side_effect = UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid byte")

        result = run_safe(["python", "-c", "print('test')"], text=True)

        assert result.returncode == -2
        assert result.stdout == ""
        assert "Encoding" in result.stderr

    def test_run_safe_default_utf8_encoding_for_text_mode(self):
        """Test run_safe uses UTF-8 encoding by default in text mode."""
        # Just verify it doesn't raise an error
        result = run_safe(["python", "-c", "print('test')"], capture_output=True, text=True)
        assert result.returncode == 0

    def test_run_safe_custom_encoding(self):
        """Test run_safe accepts custom encoding."""
        result = run_safe(["python", "-c", "print('test')"], capture_output=True, text=True, encoding="ascii")
        assert result.returncode == 0

    def test_run_safe_python_script_output(self):
        """Test run_safe captures Python script output."""
        script = "import sys; print('stdout'); print('stderr', file=sys.stderr)"
        result = run_safe(["python", "-c", script], capture_output=True, text=True)
        assert result.returncode == 0
        assert "stdout" in result.stdout
        assert "stderr" in result.stderr

    def test_run_safe_multiline_output(self):
        """Test run_safe captures multiline output."""
        script = "print('line1'); print('line2'); print('line3')"
        result = run_safe(["python", "-c", script], capture_output=True, text=True)
        assert result.returncode == 0
        assert "line1" in result.stdout
        assert "line2" in result.stdout
        assert "line3" in result.stdout

    def test_run_safe_exit_code_preservation(self):
        """Test run_safe preserves various exit codes."""
        for exit_code in [0, 1, 2, 42, 127]:
            result = run_safe(["python", "-c", f"exit({exit_code})"])
            assert result.returncode == exit_code

    def test_run_safe_empty_command_raises(self):
        """Test run_safe with empty command list raises error."""
        # Empty command list should raise a ValueError
        with pytest.raises(ValueError, match="Empty command list"):
            run_safe([])

    def test_run_safe_shell_command(self):
        """Test run_safe with shell=True."""
        result = run_safe("python -c \"print('shell')\"", shell=True, capture_output=True, text=True)
        assert result.returncode == 0
        assert "shell" in result.stdout


class TestRunSafeIntegration:
    """Integration tests for run_safe that actually execute commands."""

    def test_run_safe_git_version(self):
        """Test run_safe can execute git --version."""
        result = run_safe(["git", "--version"], capture_output=True, text=True)
        assert result.returncode == 0
        assert "git version" in result.stdout.lower()

    def test_run_safe_python_version(self):
        """Test run_safe can execute python --version."""
        result = run_safe(["python", "--version"], capture_output=True, text=True)
        assert result.returncode == 0
        # Python 3 prints to stdout
        assert "python" in result.stdout.lower() or "python" in result.stderr.lower()

    def test_run_safe_pwd(self):
        """Test run_safe can execute pwd equivalent."""
        import os

        result = run_safe(["python", "-c", "import os; print(os.getcwd())"], capture_output=True, text=True)
        assert result.returncode == 0
        assert result.stdout.strip() == os.getcwd()

    def test_run_safe_with_timeout(self):
        """Test run_safe respects timeout parameter."""
        # Command that should complete quickly
        result = run_safe(["python", "-c", "print('fast')"], capture_output=True, text=True, timeout=10)
        assert result.returncode == 0

    def test_run_safe_without_capture(self):
        """Test run_safe without capture_output returns None for stdout/stderr."""
        result = run_safe(["python", "-c", "print('test')"])
        assert result.returncode == 0
        assert result.stdout is None
        assert result.stderr is None
