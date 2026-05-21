"""Tests for review_file_node."""

from agentic_devtools.orchestration.review.nodes import review_file_node


class TestReviewFileNode:
    """Tests for review_file_node."""

    def test_reviews_all_changed_files(self):
        """Produces a review comment entry for each changed file."""
        state = {"changed_files": ["a.py", "b.py", "c.py"]}
        result = review_file_node(state)
        assert len(result["review_comments"]) == 3

    def test_handles_empty_file_list(self):
        """Handles empty changed_files list gracefully."""
        result = review_file_node({"changed_files": []})
        assert result["review_comments"] == []
        assert result["status"] == "active"

    def test_handles_missing_changed_files(self):
        """Handles missing changed_files key gracefully."""
        result = review_file_node({})
        assert result["review_comments"] == []
