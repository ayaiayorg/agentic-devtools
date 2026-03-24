"""Starter workflow template: Review PR.

This is a skeleton LangGraph workflow for reviewing a pull request.
Uncomment the node functions and graph builder below, fill in the
``# TODO`` sections, and wire up your own tools.

Usage (once implemented)::

    python review-pr.py
"""

from typing import TypedDict

from langgraph.graph import END, StateGraph  # noqa: F401
from langgraph.graph.state import CompiledStateGraph  # noqa: F401

# ---------------------------------------------------------------------------
# State schema
# ---------------------------------------------------------------------------


class ReviewPRState(TypedDict, total=False):
    """State schema for the PR review workflow."""

    pr_url: str
    step: str
    status: str
    review_comments: list[str]


# ---------------------------------------------------------------------------
# Node functions — uncomment and implement each one
# ---------------------------------------------------------------------------

# def fetch_pr_node(state: ReviewPRState) -> dict:
#     """Fetch PR details from the code hosting platform.
#
#     # TODO: Implement this node — fetch PR metadata and diff.
#     """
#     return {
#         "step": "fetch_pr",
#         "status": "active",
#     }


# def review_files_node(state: ReviewPRState) -> dict:
#     """Review changed files and collect comments.
#
#     # TODO: Implement this node — iterate over changed files and
#     # produce review comments.
#     """
#     return {
#         "step": "review_files",
#         "review_comments": ["Example comment"],
#     }


# def post_feedback_node(state: ReviewPRState) -> dict:
#     """Post review feedback to the pull request.
#
#     # TODO: Implement this node — post comments back to the PR.
#     """
#     return {
#         "step": "post_feedback",
#     }


# def completion_node(state: ReviewPRState) -> dict:
#     """Mark the review workflow as complete.
#
#     # TODO: Implement this node — finalise the review.
#     """
#     return {
#         "step": "completion",
#         "status": "completed",
#     }


# ---------------------------------------------------------------------------
# Graph builder — uncomment and customise
# ---------------------------------------------------------------------------

# def build_review_graph(checkpointer=None) -> CompiledStateGraph:
#     """Construct and compile the PR review StateGraph."""
#     graph = StateGraph(ReviewPRState)
#
#     graph.add_node("fetch_pr", fetch_pr_node)
#     graph.add_node("review_files", review_files_node)
#     graph.add_node("post_feedback", post_feedback_node)
#     graph.add_node("completion", completion_node)
#
#     graph.set_entry_point("fetch_pr")
#
#     graph.add_edge("fetch_pr", "review_files")
#     graph.add_edge("review_files", "post_feedback")
#     graph.add_edge("post_feedback", "completion")
#     graph.add_edge("completion", END)
#
#     return graph.compile(checkpointer=checkpointer)


# ---------------------------------------------------------------------------
# Quick demo — uncomment once the nodes are implemented
# ---------------------------------------------------------------------------

# if __name__ == "__main__":
#     compiled = build_review_graph()
#     result = compiled.invoke({"pr_url": "https://example.com/pr/1"})
#     print("Final state:")
#     for key, value in sorted(result.items()):
#         print(f"  {key}: {value}")
