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



class TestGenerateReviewPrompts:
    """Tests for generate_review_prompts function."""

    def test_generates_prompts_for_files(self, tmp_path):
        """Test generates prompt files for PR files."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.azure_devops.review_commands import generate_review_prompts

        pr_details = {
            "files": [
                {"path": "/src/file1.ts", "changeType": "edit"},
                {"path": "/src/file2.ts", "changeType": "add"},
            ],
            "threads": [],
        }

        # Patch the scripts directory location
        with patch("agdt_ai_helpers.cli.azure_devops.review_commands.Path") as mock_path:
            # Make the path operations work with tmp_path
            mock_path.return_value.parent.parent.parent.parent.parent = tmp_path
            mock_path.return_value.__truediv__ = lambda self, x: tmp_path / x

            # Actually call the function but with simplified setup
            from agdt_ai_helpers.cli.azure_devops.review_commands import generate_review_prompts

            # Minimal patching to avoid complex path issues
            with patch.object(
                __import__("agdt_ai_helpers.cli.azure_devops.review_commands", fromlist=["get_state_dir"]),
                "get_state_dir",
                return_value=tmp_path,
            ):
                prompts_count, skipped_reviewed, skipped_not_on_branch, prompts_dir = generate_review_prompts(
                    pull_request_id=123,
                    pr_details=pr_details,
                    include_reviewed=True,  # Don't skip any
                    files_on_branch=None,  # Don't filter by branch files
                )

        assert prompts_count == 2
        assert skipped_reviewed == 0
        assert skipped_not_on_branch == 0

    def test_skips_reviewed_files(self, tmp_path):
        """Test skips files already marked as reviewed."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.azure_devops.review_commands import generate_review_prompts

        pr_details = {
            "files": [
                {"path": "/src/file1.ts", "changeType": "edit"},
            ],
            "threads": [],
            # Note: The function looks for "reviewer" (singular) not "reviewers"
            "reviewer": {
                "reviewedFiles": ["/src/file1.ts"],
            },
        }

        with patch.object(
            __import__("agdt_ai_helpers.cli.azure_devops.review_commands", fromlist=["get_state_dir"]),
            "get_state_dir",
            return_value=tmp_path,
        ):
            prompts_count, skipped_reviewed, skipped_not_on_branch, _ = generate_review_prompts(
                pull_request_id=123,
                pr_details=pr_details,
                include_reviewed=False,  # Skip reviewed files
                files_on_branch=None,
            )

        assert prompts_count == 0
        assert skipped_reviewed == 1

    def test_skips_files_not_on_branch(self, tmp_path):
        """Test skips files not in the branch changes."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.azure_devops.review_commands import generate_review_prompts

        pr_details = {
            "files": [
                {"path": "/src/file1.ts", "changeType": "edit"},
                {"path": "/src/file2.ts", "changeType": "edit"},
            ],
            "threads": [],
        }

        # Only file1.ts is actually on the branch
        files_on_branch = {"/src/file1.ts"}

        with patch.object(
            __import__("agdt_ai_helpers.cli.azure_devops.review_commands", fromlist=["get_state_dir"]),
            "get_state_dir",
            return_value=tmp_path,
        ):
            prompts_count, skipped_reviewed, skipped_not_on_branch, _ = generate_review_prompts(
                pull_request_id=123,
                pr_details=pr_details,
                include_reviewed=True,
                files_on_branch=files_on_branch,
            )

        assert prompts_count == 1
        assert skipped_not_on_branch == 1
