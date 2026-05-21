"""Tests for scaffold_node."""

from agentic_devtools.orchestration.review.nodes import scaffold_node


class TestScaffoldNode:
    """Tests for scaffold_node."""

    def test_returns_active_status(self):
        """Returns active status after scaffolding."""
        result = scaffold_node({"pr_id": 123})
        assert result["step"] == "scaffold"
        assert result["status"] == "active"

    def test_includes_event(self):
        """Includes a scaffold_complete event."""
        result = scaffold_node({"pr_id": 123})
        assert any(e["event"] == "scaffold_complete" for e in result["events"])
