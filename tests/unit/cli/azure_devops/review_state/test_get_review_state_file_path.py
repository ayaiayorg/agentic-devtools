"""Tests for get_review_state_file_path function."""

from pathlib import Path
from unittest.mock import patch

from agentic_devtools.cli.azure_devops import review_state as rs_module
from agentic_devtools.cli.azure_devops.review_state import get_review_state_file_path


class TestGetReviewStateFilePath:
    """Tests for get_review_state_file_path function."""

    def test_returns_expected_path(self, tmp_path):
        """Test that the correct path is returned for a given PR ID."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            result = get_review_state_file_path(25365)
        expected = tmp_path / "pull-request-review" / "prompts" / "25365" / "review-state.json"
        assert result == expected

    def test_different_pr_ids_give_different_paths(self, tmp_path):
        """Test that different PR IDs result in different paths."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            path1 = get_review_state_file_path(1000)
            path2 = get_review_state_file_path(2000)
        assert path1 != path2
        assert "1000" in str(path1)
        assert "2000" in str(path2)

    def test_path_ends_with_review_state_json(self, tmp_path):
        """Test that the filename is always review-state.json."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            result = get_review_state_file_path(999)
        assert result.name == "review-state.json"

    def test_returns_path_object(self, tmp_path):
        """Test that the return type is a Path object."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            result = get_review_state_file_path(1)
        assert isinstance(result, Path)
