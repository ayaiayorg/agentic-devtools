"""Tests for run_coverage_check."""

from __future__ import annotations

from unittest.mock import patch

from agentic_devtools.cli.checks.tests import run_coverage_check

MODULE = "agentic_devtools.cli.checks.tests"


class TestRunCoverageCheck:
    """Tests for run_coverage_check (sequential wrapper)."""

    @patch(f"{MODULE}.run_one_coverage")
    def test_all_pass(self, mock_one, capsys):
        mock_one.return_value = (True, "ok")
        total, failures = run_coverage_check(["a.py", "b.py"], cwd="/tmp")
        assert total == 2
        assert failures == 0

    @patch(f"{MODULE}.run_one_coverage")
    def test_some_fail(self, mock_one, capsys):
        mock_one.side_effect = [(True, "ok"), (False, "FAIL: b.py")]
        total, failures = run_coverage_check(["a.py", "b.py"], cwd="/tmp")
        assert total == 2
        assert failures == 1

    @patch(f"{MODULE}.run_one_coverage")
    def test_prints_output(self, mock_one, capsys):
        mock_one.return_value = (True, "test output line")
        run_coverage_check(["a.py"])
        captured = capsys.readouterr()
        assert "test output line" in captured.out
