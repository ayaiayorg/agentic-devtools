"""
Tests for pr_summary_commands module.

Covers:
- Deprecated generate_overarching_pr_comments function returns False
"""

from agentic_devtools.cli.azure_devops.pr_summary_commands import (
    generate_overarching_pr_comments,
)


class TestGenerateOverarchingPrComments:
    """Tests for deprecated generate_overarching_pr_comments function."""

    def test_returns_false_deprecated(self, capsys):
        """Deprecated function should return False and print deprecation message."""
        result = generate_overarching_pr_comments()

        assert result is False
        captured = capsys.readouterr()
        assert "deprecated" in captured.err
