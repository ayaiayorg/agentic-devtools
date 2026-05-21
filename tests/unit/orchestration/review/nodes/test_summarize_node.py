"""Tests for summarize_node."""

from agentic_devtools.orchestration.review.nodes import summarize_node


class TestSummarizeNode:
    """Tests for summarize_node."""

    def test_needs_work_when_review_is_not_ready_for_approval(self):
        """Decision remains 'needs-work' until review output is ready."""
        state = {
            "review_comments": [
                {"file": "a.py", "status": "reviewed", "comments": []},
            ],
        }
        result = summarize_node(state)
        assert result["decision"] == "needs-work"

    def test_approves_when_no_issues_and_review_is_ready(self):
        """Decision is 'approved' when no issues and approval is explicitly allowed."""
        state = {
            "review_comments": [
                {"file": "a.py", "status": "reviewed", "comments": []},
            ],
            "review_ready_for_approval": True,
        }
        result = summarize_node(state)
        assert result["decision"] == "approved"

    def test_needs_work_when_review_ready_flag_is_explicitly_false(self):
        """Decision remains 'needs-work' when readiness flag is explicitly false."""
        state = {
            "review_comments": [
                {"file": "a.py", "status": "reviewed", "comments": []},
            ],
            "review_ready_for_approval": False,
        }
        result = summarize_node(state)
        assert result["decision"] == "needs-work"

    def test_needs_work_when_issues_found(self):
        """Decision is 'needs-work' when comments have issues."""
        state = {
            "review_comments": [
                {"file": "a.py", "status": "reviewed", "comments": ["Fix this"]},
            ],
        }
        result = summarize_node(state)
        assert result["decision"] == "needs-work"

    def test_includes_summary_text(self):
        """Includes a human-readable summary."""
        state = {"review_comments": [{"file": "a.py", "comments": []}]}
        result = summarize_node(state)
        assert "1 file(s)" in result["review_summary"]
