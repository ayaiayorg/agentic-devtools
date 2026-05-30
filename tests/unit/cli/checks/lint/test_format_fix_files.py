"""Tests for format_fix_files."""

from __future__ import annotations

from subprocess import CompletedProcess
from unittest.mock import patch

from agentic_devtools.cli.checks.lint import format_fix_files

MODULE = "agentic_devtools.cli.checks.lint"


class TestFormatFixFiles:
    """Tests for format_fix_files."""

    def test_empty_files_returns_pass(self):
        passed, output = format_fix_files([])
        assert passed is True
        assert output == ""

    @patch(f"{MODULE}.subprocess.run")
    def test_no_changes(self, mock_run):
        mock_run.side_effect = [
            CompletedProcess(args=[], returncode=0, stdout="", stderr="2 files left unchanged\n"),
            CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
        ]
        passed, output = format_fix_files(["a.py", "b.py"], cwd="/tmp")
        assert passed is True
        assert "left unchanged" in output

    @patch(f"{MODULE}.subprocess.run")
    def test_files_reformatted(self, mock_run):
        mock_run.side_effect = [
            CompletedProcess(args=[], returncode=0, stdout="", stderr="1 file reformatted\n"),
            CompletedProcess(args=[], returncode=0, stdout="a.py\n", stderr=""),
        ]
        passed, output = format_fix_files(["a.py"])
        assert passed is False
        assert "reformatted" in output

    @patch(f"{MODULE}.subprocess.run")
    def test_calls_ruff_format_then_git_diff_limited_to_files(self, mock_run):
        mock_run.side_effect = [
            CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
        ]
        format_fix_files(["a.py"], cwd="/x")
        assert mock_run.call_count == 2
        first_call = mock_run.call_args_list[0]
        assert "ruff" in first_call[0][0]
        second_call = mock_run.call_args_list[1]
        assert "git" in second_call[0][0]
        assert second_call[0][0][-1] == "a.py"

    @patch(f"{MODULE}.subprocess.run")
    def test_ruff_format_error_returns_error_output(self, mock_run):
        mock_run.return_value = CompletedProcess(args=[], returncode=2, stdout="", stderr="parse error")
        passed, output = format_fix_files(["a.py"])
        assert passed is False
        assert output.startswith("ERROR: ruff format failed")
