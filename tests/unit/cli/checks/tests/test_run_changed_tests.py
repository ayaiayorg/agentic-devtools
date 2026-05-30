"""Tests for run_changed_tests."""

from __future__ import annotations

from subprocess import CompletedProcess
from unittest.mock import patch

from agentic_devtools.cli.checks.tests import run_changed_tests

MODULE = "agentic_devtools.cli.checks.tests"


class TestRunChangedTests:
    """Tests for run_changed_tests."""

    def test_empty_list_returns_pass(self):
        passed, output = run_changed_tests([])
        assert passed is True
        assert output == ""

    @patch(f"{MODULE}.subprocess.run")
    def test_success(self, mock_run):
        mock_run.return_value = CompletedProcess(args=[], returncode=0, stdout="3 passed in 0.5s\n", stderr="")
        passed, output = run_changed_tests(["tests/test_foo.py"], cwd="/tmp")
        assert passed is True
        assert "3 passed" in output

    @patch(f"{MODULE}.subprocess.run")
    def test_failure(self, mock_run):
        mock_run.return_value = CompletedProcess(args=[], returncode=1, stdout="1 failed\n", stderr="")
        passed, output = run_changed_tests(["tests/test_foo.py"])
        assert passed is False
        assert "1 failed" in output

    @patch(f"{MODULE}.subprocess.run")
    def test_passes_no_cov_and_quiet(self, mock_run):
        mock_run.return_value = CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        run_changed_tests(["tests/test_foo.py"])
        args = mock_run.call_args[0][0]
        assert "--no-cov" in args
        assert "-q" in args
