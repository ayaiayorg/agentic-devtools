"""Graph builder utility for constructing LangGraph StateGraph instances."""

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from .pilot_workflow import (
    checklist_creation_node,
    commit_node,
    completion_node,
    implementation_node,
    implementation_review_node,
    initiate_node,
    planning_gate_node,
    planning_node,
    pull_request_node,
    route_after_implementation,
    route_after_initiate,
    route_after_plan,
    route_after_verify,
    setup_node,
    verification_node,
)
from .state_schema import WorkOnIssueState


def build_work_on_issue_graph(checkpointer=None) -> CompiledStateGraph:
    """Construct and compile the work-on-jira-issue StateGraph.

    Args:
        checkpointer: Optional LangGraph checkpointer (e.g. ``SqliteSaver``)
            for durable state persistence.  Pass ``None`` for in-memory-only
            execution (useful for tests and diagram generation).

    Returns:
        A compiled ``CompiledStateGraph`` ready for invocation.
    """
    graph = StateGraph(WorkOnIssueState)

    # -- nodes ---------------------------------------------------------------
    graph.add_node("initiate", initiate_node)
    graph.add_node("setup", setup_node)
    graph.add_node("planning", planning_node)
    graph.add_node("planning_gate", planning_gate_node)
    graph.add_node("checklist_creation", checklist_creation_node)
    graph.add_node("implementation", implementation_node)
    graph.add_node("implementation_review", implementation_review_node)
    graph.add_node("verification", verification_node)
    graph.add_node("commit", commit_node)
    graph.add_node("pull_request", pull_request_node)
    graph.add_node("completion", completion_node)

    # -- entry point ---------------------------------------------------------
    graph.set_entry_point("initiate")

    # -- edges ---------------------------------------------------------------
    graph.add_conditional_edges("initiate", route_after_initiate, {"setup": "setup", "planning": "planning"})
    graph.add_edge("setup", "planning")
    graph.add_conditional_edges(
        "planning",
        route_after_plan,
        {"checklist_creation": "checklist_creation", "planning_gate": "planning_gate"},
    )
    graph.add_conditional_edges(
        "planning_gate",
        route_after_plan,
        {"checklist_creation": "checklist_creation", "planning_gate": "planning_gate"},
    )
    graph.add_edge("checklist_creation", "implementation")
    graph.add_conditional_edges(
        "implementation",
        route_after_implementation,
        {"implementation_review": "implementation_review"},
    )
    graph.add_edge("implementation_review", "verification")
    graph.add_conditional_edges(
        "verification",
        route_after_verify,
        {"commit": "commit", "implementation": "implementation"},
    )
    graph.add_edge("commit", "pull_request")
    graph.add_edge("pull_request", "completion")
    graph.add_edge("completion", END)

    return graph.compile(checkpointer=checkpointer)
