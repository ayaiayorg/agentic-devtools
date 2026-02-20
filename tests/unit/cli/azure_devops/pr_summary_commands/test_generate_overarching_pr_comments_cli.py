"""
Tests for pr_summary_commands module.

Covers:
- Return value behavior of generate_overarching_pr_comments
- Early exit scenarios (no files, no threads, dry run)
- Helper functions for path normalization, sorting, and link building
"""

from unittest.mock import patch

from agentic_devtools.cli.azure_devops.pr_summary_commands import (
    generate_overarching_pr_comments_cli,
)


class TestGenerateOverarchingPrCommentsCli:
    """Tests for CLI entry point."""

    def test_cli_calls_main_function(self, temp_state_dir, clear_state_before):
        """CLI entry point should call generate_overarching_pr_comments."""
        with patch(
            "agentic_devtools.cli.azure_devops.pr_summary_commands.generate_overarching_pr_comments"
        ) as mock_func:
            mock_func.return_value = True
            generate_overarching_pr_comments_cli()
            mock_func.assert_called_once()
