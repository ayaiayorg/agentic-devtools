"""Tests for lint_files."""

from __future__ import annotations

from subprocess import CompletedProcess
from unittest.mock import patch

from agentic_devtools.cli.checks.lint import lint_files

MODULE = "agentic_devtools.cli.checks.lint"


class TestLintFiles:
    """Tests for lint_files."""

    def test_empty_files_returns_pass(self):
        passed, output = lint_files([])
        assert passed is True
        assert output == ""

    @patch(f"{MODULE}.subprocess.run")
    def test_success(self, mock_run):
        mock_run.return_value = CompletedProcess(args=[], returncode=0, stdout="All checks passed!\n", stderr="")
        passed, output = lint_files(["foo.py"], cwd="/tmp")
        assert passed is True
        assert "All checks passed!" in output

    @patch(f"{MODULE}.subprocess.run")
    def test_failure(self, mock_run):
        mock_run.return_value = CompletedProcess(
            args=[], returncode=1, stdout="foo.py:1: E501 line too long\n", stderr=""
        )
        passed, output = lint_files(["foo.py"])
        assert passed is False
        assert "E501" in output

    @patch(f"{MODULE}.subprocess.run")
    def test_passes_cwd(self, mock_run):
        mock_run.return_value = CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        lint_files(["foo.py"], cwd="/my/dir")
        assert mock_run.call_args[1]["cwd"] == "/my/dir"

    @patch(f"{MODULE}.subprocess.run")
    def test_combines_stdout_stderr(self, mock_run):
        mock_run.return_value = CompletedProcess(args=[], returncode=1, stdout="stdout\n", stderr="stderr\n")
        _, output = lint_files(["foo.py"])
        assert "stdout" in output
        assert "stderr" in output
