"""Tests for PR review graph builder."""

from agentic_devtools.orchestration.review.graph_builder import build_pr_review_graph


class TestBuildPrReviewGraph:
    """Tests for build_pr_review_graph."""

    def test_graph_compiles_successfully(self):
        """Graph compiles without errors."""
        graph = build_pr_review_graph()
        assert graph is not None

    def test_graph_has_expected_nodes(self):
        """Graph contains all expected node names."""
        graph = build_pr_review_graph()
        # The compiled graph should have the nodes we defined
        node_names = set(graph.get_graph().nodes.keys())
        expected = {"fetch_pr_details", "scaffold", "review_files", "summarize", "complete"}
        # LangGraph adds __start__ and __end__ nodes
        assert expected.issubset(node_names)

    def test_graph_invocation_with_minimal_state(self):
        """Graph can be invoked with minimal valid state."""
        from unittest.mock import patch

        # Mock the PR details fetch to avoid real API calls
        with patch("agentic_devtools.orchestration.review.graph_builder.fetch_pr_details_node") as mock_fetch:
            graph = build_pr_review_graph()
            mock_fetch.return_value = {
                "step": "fetch_pr_details",
                "status": "active",
                "pr_title": "Test PR",
                "pr_description": "Test description",
                "source_branch": "feature/test",
                "target_branch": "main",
                "changed_files": ["src/test.py"],
                "events": [{"event": "fetch_pr_details_complete", "timestamp": "2024-01-01T00:00:00Z"}],
            }

            result = graph.invoke(
                {
                    "pr_id": 123,
                    "state_dir": "/tmp/test",
                    "config": {},
                    "step": "init",
                    "status": "active",
                    "review_comments": [],
                    "events": [],
                }
            )

            assert result["status"] == "completed"
            assert result["step"] == "completion"

    def test_graph_stops_on_fetch_failure(self):
        """Graph stops early when fetch step fails."""
        from unittest.mock import patch

        with patch("agentic_devtools.orchestration.review.graph_builder.fetch_pr_details_node") as mock_fetch:
            graph = build_pr_review_graph()
            mock_fetch.return_value = {
                "step": "fetch_pr_details",
                "status": "failed",
                "error": "boom",
                "events": [{"event": "fetch_pr_details_failed", "timestamp": "2024-01-01T00:00:00Z"}],
            }

            result = graph.invoke(
                {
                    "pr_id": 123,
                    "state_dir": "/tmp/test",
                    "config": {},
                    "step": "init",
                    "status": "active",
                    "review_comments": [],
                    "events": [],
                }
            )

            assert result["status"] == "failed"
            assert result["step"] == "fetch_pr_details"
            assert result["error"] == "boom"
