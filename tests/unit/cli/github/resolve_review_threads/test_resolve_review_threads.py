"""Tests for the resolve_review_threads core function."""

from unittest.mock import patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli.github.resolve_review_threads import (
    resolve_review_threads,
)

_MODULE = "agentic_devtools.cli.github.resolve_review_threads"


@pytest.fixture
def temp_state(tmp_path):
    """Create a temporary state directory."""
    with patch.object(state, "get_state_dir", return_value=tmp_path):
        state.clear_state()
        yield tmp_path


class TestResolveReviewThreads:
    """Tests for resolve_review_threads."""

    @patch(f"{_MODULE}._resolve_and_verify")
    @patch(f"{_MODULE}._fetch_review_comment_ids")
    def test_with_review_id(self, mock_fetch_ids, mock_rav, temp_state):
        """Use review_id to fetch comment IDs then resolve."""
        mock_fetch_ids.return_value = [10, 20]
        mock_rav.return_value = {
            "threadsResolved": 2,
            "threadsFailed": 0,
            "alreadyResolved": 0,
            "totalTargeted": 2,
            "details": [],
            "verified": True,
        }

        result = resolve_review_threads(42, "owner/repo", review_id=999)

        mock_fetch_ids.assert_called_once_with(42, "owner/repo", 999)
        mock_rav.assert_called_once_with(42, "owner", "repo", {10, 20})
        assert result["prNumber"] == 42
        assert result["repo"] == "owner/repo"
        assert result["verified"] is True
        # Verify state keys written
        assert state.get_value("github.threads_resolved_count") == 2
        assert state.get_value("github.threads_failed_count") == 0
        assert state.get_value("github.threads_resolution_verified") is True

    @patch(f"{_MODULE}._resolve_and_verify")
    def test_with_comment_ids(self, mock_rav, temp_state):
        """Use comment_ids directly without fetching."""
        mock_rav.return_value = {
            "threadsResolved": 1,
            "threadsFailed": 0,
            "alreadyResolved": 1,
            "totalTargeted": 2,
            "details": [],
            "verified": True,
        }

        result = resolve_review_threads(42, "owner/repo", comment_ids=[10, 20])

        mock_rav.assert_called_once_with(42, "owner", "repo", {10, 20})
        assert result["prNumber"] == 42
        assert state.get_value("github.threads_already_resolved_count") == 1

    @patch(f"{_MODULE}._fetch_review_comment_ids")
    def test_empty_comment_ids_returns_immediately(self, mock_fetch_ids, temp_state):
        """Empty target list returns immediate success."""
        mock_fetch_ids.return_value = []

        result = resolve_review_threads(42, "owner/repo", review_id=999)

        assert result["totalTargeted"] == 0
        assert result["verified"] is True
        assert state.get_value("github.threads_resolved_count") == 0

    def test_neither_review_nor_comments_raises(self, temp_state):
        """Raise ValueError when neither review_id nor comment_ids given."""
        with pytest.raises(ValueError, match="Either review_id or comment_ids"):
            resolve_review_threads(42, "owner/repo")

    def test_empty_list_comment_ids_returns_immediately(self, temp_state):
        """Passing comment_ids=[] returns immediate success without falling back to review_id."""
        result = resolve_review_threads(42, "owner/repo", review_id=999, comment_ids=[])

        assert result["totalTargeted"] == 0
        assert result["verified"] is True
        assert state.get_value("github.threads_resolved_count") == 0

    @patch(f"{_MODULE}._resolve_and_verify")
    def test_comment_ids_take_precedence_over_review_id(self, mock_rav, temp_state):
        """When both provided, comment_ids are used directly."""
        mock_rav.return_value = {
            "threadsResolved": 1,
            "threadsFailed": 0,
            "alreadyResolved": 0,
            "totalTargeted": 1,
            "details": [],
            "verified": True,
        }

        resolve_review_threads(42, "owner/repo", review_id=999, comment_ids=[10])

        # _fetch_review_comment_ids should NOT be called
        mock_rav.assert_called_once_with(42, "owner", "repo", {10})
