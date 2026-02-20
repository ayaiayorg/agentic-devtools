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



class TestNormalizeRepoPath:
    """Tests for normalize_repo_path function."""

    def test_basic_path(self):
        """Test normalization of basic path."""
        result = normalize_repo_path("src/app/file.ts")
        assert result == "/src/app/file.ts"

    def test_path_with_leading_slash(self):
        """Test path with leading slash."""
        result = normalize_repo_path("/src/app/file.ts")
        assert result == "/src/app/file.ts"

    def test_path_with_backslashes(self):
        """Test path with Windows backslashes."""
        result = normalize_repo_path("src\\app\\file.ts")
        assert result == "/src/app/file.ts"

    def test_empty_path(self):
        """Test empty path returns None."""
        result = normalize_repo_path("")
        assert result is None

    def test_none_path(self):
        """Test None path returns None."""
        result = normalize_repo_path(None)
        assert result is None

    def test_whitespace_only(self):
        """Test whitespace-only path returns None."""
        result = normalize_repo_path("   ")
        assert result is None
