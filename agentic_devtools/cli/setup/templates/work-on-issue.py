"""Starter workflow template: Work on Issue.

This is a self-contained LangGraph workflow graph modeled after the
agentic-devtools pilot workflow pattern.  It defines a simplified
issue-processing pipeline with six nodes:

    initiate → planning → implementation → verification → commit → completion

The ``route_after_verify`` conditional edge retries implementation up to
``MAX_RETRIES`` times when verification reports an error.

Usage::

    python work-on-issue.py

Customise the node functions to call real tools (Jira, Git, test runners,
etc.) and adjust the graph edges to match your team's workflow.
"""

import operator
from datetime import datetime, timezone
from typing import Annotated, TypedDict

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

# ---------------------------------------------------------------------------
# State schema
# ---------------------------------------------------------------------------

MAX_RETRIES = 3
"""Maximum verification retry loops before forcing a commit."""


class WorkOnIssueEvent(TypedDict):
    """A single event entry in the workflow audit trail."""

    event: str
    timestamp: str


class WorkOnIssueState(TypedDict, total=False):
    """State schema for the work-on-issue workflow.

    ``events`` uses an ``operator.add`` reducer for append-only logging.
    All other fields use default last-writer-wins semantics.
    """

    issue_key: str
    step: str
    status: str
    plan: str
    error: str | None
    retry_count: int
    events: Annotated[list[WorkOnIssueEvent], operator.add]
    human_approved: bool


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _utc_now() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------


def initiate_node(state: WorkOnIssueState) -> dict:
    """Entry point — set initial step and status."""
    return {
        "step": "initiate",
        "status": "active",
        "events": [{"event": "initiate_completed", "timestamp": _utc_now()}],
    }


def planning_node(state: WorkOnIssueState) -> dict:
    """Analyse the issue and prepare a plan."""
    return {
        "step": "planning",
        "plan": "Plan for " + state.get("issue_key", "UNKNOWN"),
        "events": [{"event": "planning_completed", "timestamp": _utc_now()}],
    }


def implementation_node(state: WorkOnIssueState) -> dict:
    """Execute the implementation work."""
    return {
        "step": "implementation",
        "events": [{"event": "implementation_completed", "timestamp": _utc_now()}],
    }


def verification_node(state: WorkOnIssueState) -> dict:
    """Run tests and quality gates."""
    retry_count = state.get("retry_count", 0)
    existing_error = state.get("error")
    if existing_error:
        retry_count += 1
    return {
        "step": "verification",
        "error": existing_error,
        "retry_count": retry_count,
        "events": [{"event": "verification_completed", "timestamp": _utc_now()}],
    }


def commit_node(state: WorkOnIssueState) -> dict:
    """Stage and commit changes."""
    return {
        "step": "commit",
        "events": [{"event": "commit_completed", "timestamp": _utc_now()}],
    }


def completion_node(state: WorkOnIssueState) -> dict:
    """Mark the workflow as complete."""
    return {
        "step": "completion",
        "status": "completed",
        "events": [{"event": "completion_completed", "timestamp": _utc_now()}],
    }


# ---------------------------------------------------------------------------
# Conditional edge
# ---------------------------------------------------------------------------


def route_after_verify(state: WorkOnIssueState) -> str:
    """Route back to implementation on retryable error, otherwise commit."""
    if state.get("error") and state.get("retry_count", 0) < MAX_RETRIES:
        return "implementation"
    return "commit"


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------


def build_graph(checkpointer=None) -> CompiledStateGraph:
    """Construct and compile the work-on-issue StateGraph."""
    graph = StateGraph(WorkOnIssueState)

    graph.add_node("initiate", initiate_node)
    graph.add_node("planning", planning_node)
    graph.add_node("implementation", implementation_node)
    graph.add_node("verification", verification_node)
    graph.add_node("commit", commit_node)
    graph.add_node("completion", completion_node)

    graph.set_entry_point("initiate")

    graph.add_edge("initiate", "planning")
    graph.add_edge("planning", "implementation")
    graph.add_edge("implementation", "verification")
    graph.add_conditional_edges(
        "verification",
        route_after_verify,
        {"commit": "commit", "implementation": "implementation"},
    )
    graph.add_edge("commit", "completion")
    graph.add_edge("completion", END)

    return graph.compile(checkpointer=checkpointer)


# ---------------------------------------------------------------------------
# Quick demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    compiled = build_graph()
    result = compiled.invoke({"issue_key": "EXAMPLE-1"})
    print("Final state:")
    for key, value in sorted(result.items()):
        print(f"  {key}: {value}")
