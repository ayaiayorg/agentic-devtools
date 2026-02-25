"""Tests for parse_jira_error_report function."""

from unittest.mock import patch

from agentic_devtools.cli.jira.parse_error_report import parse_jira_error_report


class TestParseJiraErrorReport:
    """Tests for parse_jira_error_report function."""

    def test_prints_error_when_path_not_set(self, capsys):
        """Should print an error message when error_file_path is not set."""
        with patch(
            "agentic_devtools.cli.jira.parse_error_report.get_jira_value",
            return_value=None,
        ):
            parse_jira_error_report()

        captured = capsys.readouterr()
        assert "error_file_path" in captured.out.lower() or "Error" in captured.out

    def test_prints_error_when_file_not_found(self, capsys, tmp_path):
        """Should print error when the specified file does not exist."""
        nonexistent = str(tmp_path / "missing.txt")

        with patch(
            "agentic_devtools.cli.jira.parse_error_report.get_jira_value",
            return_value=nonexistent,
        ):
            parse_jira_error_report()

        captured = capsys.readouterr()
        assert "not found" in captured.out.lower() or "Error" in captured.out

    def test_function_is_callable(self):
        """Verify parse_jira_error_report is importable and callable."""
        assert callable(parse_jira_error_report)
