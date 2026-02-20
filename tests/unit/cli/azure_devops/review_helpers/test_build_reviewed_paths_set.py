"""Tests for the review_commands module and helper functions."""

from agdt_ai_helpers.cli.azure_devops.review_helpers import (
    build_reviewed_paths_set,
)


class TestBuildReviewedPathsSet:
    """Tests for build_reviewed_paths_set function."""

    def test_empty_pr_details(self):
        """Test empty PR details returns empty set."""
        result = build_reviewed_paths_set({})
        assert result == set()

    def test_no_reviewer_data(self):
        """Test PR details without reviewer key returns empty set."""
        pr_details = {"pullRequest": {"id": 123}}
        result = build_reviewed_paths_set(pr_details)
        assert result == set()

    def test_none_reviewer_data(self):
        """Test PR details with None reviewer returns empty set."""
        pr_details = {"reviewer": None}
        result = build_reviewed_paths_set(pr_details)
        assert result == set()

    def test_empty_reviewed_files(self):
        """Test empty reviewedFiles returns empty set."""
        pr_details = {"reviewer": {"reviewedFiles": []}}
        result = build_reviewed_paths_set(pr_details)
        assert result == set()

    def test_none_reviewed_files(self):
        """Test None reviewedFiles returns empty set."""
        pr_details = {"reviewer": {"reviewedFiles": None}}
        result = build_reviewed_paths_set(pr_details)
        assert result == set()

    def test_single_reviewed_file(self):
        """Test single reviewed file is normalized."""
        pr_details = {"reviewer": {"reviewedFiles": ["/src/file.ts"]}}
        result = build_reviewed_paths_set(pr_details)
        assert "/src/file.ts" in result

    def test_multiple_reviewed_files(self):
        """Test multiple reviewed files are normalized."""
        pr_details = {"reviewer": {"reviewedFiles": ["/src/file1.ts", "/src/file2.ts"]}}
        result = build_reviewed_paths_set(pr_details)
        assert len(result) == 2
        assert "/src/file1.ts" in result
        assert "/src/file2.ts" in result

    def test_paths_are_lowercase(self):
        """Test paths are normalized to lowercase."""
        pr_details = {"reviewer": {"reviewedFiles": ["/SRC/FILE.TS"]}}
        result = build_reviewed_paths_set(pr_details)
        assert "/src/file.ts" in result
        assert "/SRC/FILE.TS" not in result

    def test_invalid_paths_are_skipped(self):
        """Test invalid paths (empty, None) are skipped."""
        pr_details = {"reviewer": {"reviewedFiles": ["", None, "/src/valid.ts", "   "]}}
        result = build_reviewed_paths_set(pr_details)
        assert len(result) == 1
        assert "/src/valid.ts" in result
