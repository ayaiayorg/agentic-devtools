"""Tests for the review_commands module and helper functions."""

import pytest

from agdt_ai_helpers.cli.azure_devops.review_helpers import (
    JIRA_ISSUE_KEY_PATTERN,
    build_reviewed_paths_set,
    convert_to_prompt_filename,
    extract_jira_issue_key_from_title,
    filter_threads,
    get_root_folder,
    get_threads_for_file,
    normalize_repo_path,
)



class TestPrintReviewInstructions:
    """Tests for print_review_instructions function."""

    def test_prints_basic_info(self, tmp_path, capsys):
        """Test prints basic review information."""
        from agdt_ai_helpers.cli.azure_devops.review_commands import print_review_instructions

        print_review_instructions(
            pull_request_id=123,
            prompts_dir=tmp_path,
            prompts_generated=5,
            skipped_reviewed_count=2,
        )

        captured = capsys.readouterr()
        assert "PR ID: 123" in captured.out
        assert "Prompts generated: 5" in captured.out
        assert "Skipped (already reviewed): 2" in captured.out

    def test_prints_skipped_not_on_branch(self, tmp_path, capsys):
        """Test prints skipped not on branch count when non-zero."""
        from agdt_ai_helpers.cli.azure_devops.review_commands import print_review_instructions

        print_review_instructions(
            pull_request_id=123,
            prompts_dir=tmp_path,
            prompts_generated=3,
            skipped_reviewed_count=1,
            skipped_not_on_branch_count=2,
        )

        captured = capsys.readouterr()
        assert "Skipped (not on branch" in captured.out
        assert "2" in captured.out
