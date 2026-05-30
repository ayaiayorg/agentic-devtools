"""Tests for mypy_check_files."""

from __future__ import annotations

from subprocess import CompletedProcess
from unittest.mock import patch

from agentic_devtools.cli.checks.lint import mypy_check_files

MODULE = "agentic_devtools.cli.checks.lint"


class TestMypyCheckFiles:
    """Tests for mypy_check_files."""

    def test_empty_files_returns_pass(self):
        passed, output = mypy_check_files([])
        assert passed is True
        assert output == ""

    @patch(f"{MODULE}.subprocess.run")
    def test_success(self, mock_run):
        mock_run.return_value = CompletedProcess(
            args=[], returncode=0, stdout="Success: no issues found in 3 source files\n", stderr=""
        )
        passed, output = mypy_check_files(["a.py", "b.py", "c.py"], cwd="/tmp")
        assert passed is True
        assert "Success" in output

    @patch(f"{MODULE}.subprocess.run")
    def test_failure(self, mock_run):
        mock_run.return_value = CompletedProcess(
            args=[], returncode=1, stdout="a.py:10: error: Incompatible types\n", stderr=""
        )
        passed, output = mypy_check_files(["a.py"])
        assert passed is False
        assert "error" in output

    @patch(f"{MODULE}.subprocess.run")
    def test_passes_ignore_missing_imports(self, mock_run):
        mock_run.return_value = CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        mypy_check_files(["a.py"])
        args = mock_run.call_args[0][0]
        assert "--ignore-missing-imports" in args
