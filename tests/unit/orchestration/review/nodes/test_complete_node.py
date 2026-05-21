"""Tests for complete_node."""

from agentic_devtools.orchestration.review.nodes import complete_node


class TestCompleteNode:
    """Tests for complete_node."""

    def test_marks_completed(self):
        """Sets status to completed."""
        result = complete_node({"decision": "approved"})
        assert result["status"] == "completed"
        assert result["step"] == "completion"

    def test_includes_completion_event(self):
        """Includes review_complete event."""
        result = complete_node({})
        assert any(e["event"] == "review_complete" for e in result["events"])
