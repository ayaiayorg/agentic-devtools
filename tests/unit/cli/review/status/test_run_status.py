"""Tests for agdt-review status command."""

from agentic_devtools.cli.review.status import run_status


class TestRunStatus:
    """Tests for run_status."""

    def test_prints_status_header(self, capsys):
        """Prints the status header with PR ID."""
        run_status(pr_id=123)
        captured = capsys.readouterr()
        assert "REVIEW STATUS" in captured.out
        assert "123" in captured.out

    def test_prints_overall_status(self, capsys):
        """Prints the overall status line."""
        run_status(pr_id=456)
        captured = capsys.readouterr()
        assert "Overall:" in captured.out
