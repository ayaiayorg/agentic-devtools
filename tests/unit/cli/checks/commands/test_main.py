"""Tests for main entry point."""

from __future__ import annotations

from unittest.mock import patch

from agentic_devtools.cli.checks.commands import main

MODULE = "agentic_devtools.cli.checks.commands"


class TestMain:
    """Tests for main."""

    @patch(f"{MODULE}._run_checks", return_value=0)
    def test_returns_zero_on_success(self, mock_run):
        result = main()
        assert result == 0

    @patch(f"{MODULE}._run_checks", return_value=3)
    def test_returns_failure_count(self, mock_run):
        result = main()
        assert result == 3

    @patch(f"{MODULE}.sys.argv", ["checks", "--format-fix"])
    @patch(f"{MODULE}._run_checks", return_value=0)
    def test_passes_format_fix_flag(self, mock_run):
        main()
        _, kwargs = mock_run.call_args
        assert kwargs["format_fix"] is True

    @patch(f"{MODULE}.sys.argv", ["checks"])
    @patch(f"{MODULE}._run_checks", return_value=0)
    def test_no_format_fix_by_default(self, mock_run):
        main()
        _, kwargs = mock_run.call_args
        assert kwargs["format_fix"] is False
