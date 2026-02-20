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



class TestFilterThreads:
    """Tests for filter_threads function."""

    def test_empty_threads(self):
        """Test empty list returns empty list."""
        result = filter_threads([])
        assert result == []

    def test_none_threads(self):
        """Test None returns empty list."""
        result = filter_threads(None)
        assert result == []

    def test_filters_deleted_threads(self):
        """Test deleted threads are filtered out."""
        threads = [
            {"id": 1, "isDeleted": False, "comments": [{"content": "test"}]},
            {"id": 2, "isDeleted": True, "comments": [{"content": "test"}]},
        ]
        result = filter_threads(threads)
        assert len(result) == 1
        assert result[0]["id"] == 1

    def test_filters_threads_with_deleted_comments(self):
        """Test threads with all deleted comments are filtered."""
        threads = [
            {"id": 1, "comments": [{"content": "test", "isDeleted": True}]},
        ]
        result = filter_threads(threads)
        assert len(result) == 0

    def test_keeps_partial_deleted_comments(self):
        """Test threads with some active comments are kept."""
        threads = [
            {
                "id": 1,
                "comments": [
                    {"content": "active"},
                    {"content": "deleted", "isDeleted": True},
                ],
            },
        ]
        result = filter_threads(threads)
        assert len(result) == 1
        assert len(result[0]["comments"]) == 1

    def test_filters_null_threads(self):
        """Test null/None items in thread list are filtered."""
        threads = [
            None,
            {"id": 1, "comments": [{"content": "test"}]},
        ]
        result = filter_threads(threads)
        assert len(result) == 1
        assert result[0]["id"] == 1

    def test_filters_null_comments(self):
        """Test null/None items in comments list are filtered."""
        threads = [
            {"id": 1, "comments": [None, {"content": "test"}]},
        ]
        result = filter_threads(threads)
        assert len(result) == 1
        assert len(result[0]["comments"]) == 1

    def test_does_not_mutate_original(self):
        """Test that filter_threads does not mutate the original threads."""
        original_threads = [
            {
                "id": 1,
                "comments": [
                    {"content": "active"},
                    {"content": "deleted", "isDeleted": True},
                ],
            },
        ]
        # Make a deep copy for comparison
        import copy

        original_copy = copy.deepcopy(original_threads)

        result = filter_threads(original_threads)

        # Original should be unchanged
        assert original_threads == original_copy
        # Result should have filtered comments
        assert len(result[0]["comments"]) == 1
