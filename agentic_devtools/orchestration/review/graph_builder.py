"""Graph builder for the LangGraph PR review workflow."""

from __future__ import annotations

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from .nodes import (
    complete_node,
    fetch_pr_details_node,
    review_file_node,
    scaffold_node,
    summarize_node,
)
from .state_schema import PRReviewState


def _route_after_fetch(state: dict) -> str:
    """Route to scaffold on success; end early when fetch step fails."""
    return END if state.get("status") == "failed" else "scaffold"


def build_pr_review_graph(checkpointer=None) -> CompiledStateGraph:
    """Construct and compile the PR review StateGraph.

    The graph topology is:
        fetch_pr_details → (failed: END, success: scaffold)
        scaffold → review_files → summarize → complete → END

    Args:
        checkpointer: Optional LangGraph checkpointer for persistence.

    Returns:
        A compiled LangGraph state graph ready for invocation.
    """
    graph = StateGraph(PRReviewState)

    graph.add_node("fetch_pr_details", fetch_pr_details_node)  # type: ignore[type-var]
    graph.add_node("scaffold", scaffold_node)  # type: ignore[type-var]
    graph.add_node("review_files", review_file_node)  # type: ignore[type-var]
    graph.add_node("summarize", summarize_node)  # type: ignore[type-var]
    graph.add_node("complete", complete_node)  # type: ignore[type-var]

    graph.set_entry_point("fetch_pr_details")

    graph.add_conditional_edges("fetch_pr_details", _route_after_fetch)
    graph.add_edge("scaffold", "review_files")
    graph.add_edge("review_files", "summarize")
    graph.add_edge("summarize", "complete")
    graph.add_edge("complete", END)

    return graph.compile(checkpointer=checkpointer)
