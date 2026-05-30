"""Tests for format_check_files."""

from __future__ import annotations

from subprocess import CompletedProcess
from unittest.mock import patch

from agentic_devtools.cli.checks.lint import format_check_files

MODULE = "agentic_devtools.cli.checks.lint"


class TestFormatCheckFiles:
    """Tests for format_check_files."""

    def test_empty_files_returns_pass(self):
        passed, output = format_check_files([])
        assert passed is True
        assert output == ""

    @patch(f"{MODULE}.subprocess.run")
    def test_success(self, mock_run):
        mock_run.return_value = CompletedProcess(args=[], returncode=0, stdout="", stderr="3 files already formatted\n")
        passed, output = format_check_files(["a.py", "b.py", "c.py"])
        assert passed is True

    @patch(f"{MODULE}.subprocess.run")
    def test_failure(self, mock_run):
        mock_run.return_value = CompletedProcess(args=[], returncode=1, stdout="Would reformat a.py\n", stderr="")
        passed, output = format_check_files(["a.py"])
        assert passed is False
        assert "reformat" in output

    @patch(f"{MODULE}.subprocess.run")
    def test_passes_format_check_flag(self, mock_run):
        mock_run.return_value = CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        format_check_files(["a.py"])
        args = mock_run.call_args[0][0]
        assert "--check" in args
