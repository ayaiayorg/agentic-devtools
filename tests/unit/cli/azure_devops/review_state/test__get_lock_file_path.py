"""Tests for _get_lock_file_path helper."""

from unittest.mock import patch

from agentic_devtools.cli.azure_devops import review_state as rs_module
from agentic_devtools.cli.azure_devops.review_state import _get_lock_file_path


class TestGetLockFilePath:
    """Tests for _get_lock_file_path private helper."""

    def test_returns_lock_file_in_same_directory(self, tmp_path):
        """Lock file is review-state.json.lock alongside the data file."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            result = _get_lock_file_path(12345)

        assert result.name == "review-state.json.lock"
        assert result.parent == tmp_path / "reviews"

    def test_sibling_of_review_state_file(self, tmp_path):
        """Lock file is a sibling of the data file (same parent dir)."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            from agentic_devtools.cli.azure_devops.review_state import get_review_state_file_path

            data_path = get_review_state_file_path(42)
            lock_path = _get_lock_file_path(42)

        assert data_path.parent == lock_path.parent
