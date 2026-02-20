"""
Tests for pr_summary_commands module.

Covers:
- Return value behavior of generate_overarching_pr_comments
- Early exit scenarios (no files, no threads, dry run)
- Helper functions for path normalization, sorting, and link building
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.azure_devops.pr_summary_commands import (
    FileSummary,
    FolderSummary,
    _build_comment_link,
    _build_file_link,
    _build_folder_comment,
    _filter_threads,
    _get_azure_devops_sort_key,
    _get_file_thread_status,
    _get_latest_comment_context,
    _get_root_folder,
    _get_thread_file_path,
    _normalize_repo_path,
    _post_comment,
    _sort_entries_by_path,
    _sort_folders,
    generate_overarching_pr_comments,
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
