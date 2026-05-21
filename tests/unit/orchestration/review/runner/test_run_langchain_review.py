"""Tests for run_langchain_review runner function."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.orchestration.review.runner import run_langchain_review


class TestRunLangchainReview:
    """Tests for run_langchain_review."""

    def test_invokes_graph_and_returns_final_state(self):
        """Successfully invokes the graph and returns final state."""
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = {
            "status": "completed",
            "decision": "approved",
            "step": "completion",
        }

        with patch(
            "agentic_devtools.orchestration.review.runner.build_pr_review_graph",
            return_value=mock_graph,
        ):
            with patch("agentic_devtools.orchestration.review.runner._record_session"):
                result = run_langchain_review(pr_id=123)

        assert result["status"] == "completed"
        assert result["decision"] == "approved"

    def test_exits_on_graph_failure(self):
        """Exits with code 1 when graph invocation raises."""
        mock_graph = MagicMock()
        mock_graph.invoke.side_effect = RuntimeError("Graph crashed")

        with patch(
            "agentic_devtools.orchestration.review.runner.build_pr_review_graph",
            return_value=mock_graph,
        ):
            with patch("agentic_devtools.orchestration.review.runner._record_failed_session"):
                with pytest.raises(SystemExit) as exc_info:
                    run_langchain_review(pr_id=123)
                assert exc_info.value.code == 1

    def test_exits_when_graph_returns_failed_status(self):
        """Exits with code 1 when graph returns failed final state."""
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = {
            "status": "failed",
            "error": "Changed files unavailable",
            "step": "fetch_pr_details",
        }

        with (
            patch(
                "agentic_devtools.orchestration.review.runner.build_pr_review_graph",
                return_value=mock_graph,
            ),
            patch("agentic_devtools.orchestration.review.runner._record_failed_session") as mock_record_failed,
            patch("agentic_devtools.orchestration.review.runner._record_session") as mock_record_session,
        ):
            with pytest.raises(SystemExit) as exc_info:
                run_langchain_review(pr_id=123)

        assert exc_info.value.code == 1
        mock_record_failed.assert_called_once()
        mock_record_session.assert_not_called()

    def test_passes_config_to_initial_state(self):
        """Config dict is passed to graph initial state."""
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = {"status": "completed", "decision": "approved"}

        with patch(
            "agentic_devtools.orchestration.review.runner.build_pr_review_graph",
            return_value=mock_graph,
        ):
            with patch("agentic_devtools.orchestration.review.runner._record_session"):
                run_langchain_review(pr_id=456, config={"model": "gpt-4o"})

        call_args = mock_graph.invoke.call_args[0][0]
        assert call_args["config"] == {"model": "gpt-4o"}
        assert call_args["pr_id"] == 456

    def test_passes_state_dir_to_initial_state(self):
        """State dir is passed to graph initial state."""
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = {"status": "completed", "decision": "approved"}

        with patch(
            "agentic_devtools.orchestration.review.runner.build_pr_review_graph",
            return_value=mock_graph,
        ):
            with patch("agentic_devtools.orchestration.review.runner._record_session"):
                run_langchain_review(pr_id=789, state_dir="/tmp/test-state")

        call_args = mock_graph.invoke.call_args[0][0]
        assert call_args["state_dir"] == "/tmp/test-state"
