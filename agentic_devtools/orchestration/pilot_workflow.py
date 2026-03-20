"""Stub node functions and conditional edge routing for the pilot work-on-jira-issue workflow.

All node functions are pure stubs that manipulate ``WorkOnIssueState`` without calling
real Jira, Git, or Azure DevOps systems. Real tool integration is deferred to Sub-issue 2.
"""

from datetime import datetime, timezone

from langgraph.types import interrupt

from .state_schema import WorkOnIssueState

MAX_RETRIES = 3
"""Maximum number of verification retry loops before forcing a commit."""


def _utc_now() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------


def initiate_node(state: WorkOnIssueState) -> dict:
    """Entry point: validate issue key and set initial status."""
    return {
        "step": "initiate",
        "status": "active",
        "events": [{"event": "initiate_completed", "timestamp": _utc_now()}],
    }


def setup_node(state: WorkOnIssueState) -> dict:
    """Handle worktree/branch setup when pre-flight checks fail."""
    return {
        "step": "setup",
        "error": None,
        "events": [{"event": "setup_completed", "timestamp": _utc_now()}],
    }


def planning_node(state: WorkOnIssueState) -> dict:
    """Analyse the issue and prepare a plan."""
    return {
        "step": "planning",
        "plan": "Stub plan for " + state.get("issue_key", "UNKNOWN"),
        "events": [{"event": "planning_completed", "timestamp": _utc_now()}],
    }


def planning_gate_node(state: WorkOnIssueState) -> dict:
    """Human-in-the-loop gate: wait for approval of the plan.

    Calls ``interrupt()`` to pause execution.  When the graph is resumed
    (via ``Command(resume=...)``), execution continues and the node marks
    the plan as approved.
    """
    interrupt("Waiting for human approval of plan")
    return {
        "step": "planning_gate",
        "human_approved": True,
        "events": [{"event": "plan_approved", "timestamp": _utc_now()}],
    }


def checklist_creation_node(state: WorkOnIssueState) -> dict:
    """Create the implementation checklist."""
    return {
        "step": "checklist_creation",
        "events": [{"event": "checklist_creation_completed", "timestamp": _utc_now()}],
    }


def implementation_node(state: WorkOnIssueState) -> dict:
    """Execute the implementation work."""
    return {
        "step": "implementation",
        "events": [{"event": "implementation_completed", "timestamp": _utc_now()}],
    }


def implementation_review_node(state: WorkOnIssueState) -> dict:
    """Review the completed implementation."""
    return {
        "step": "implementation_review",
        "events": [{"event": "implementation_review_completed", "timestamp": _utc_now()}],
    }


def verification_node(state: WorkOnIssueState) -> dict:
    """Run tests and quality gates."""
    return {
        "step": "verification",
        "error": None,
        "retry_count": state.get("retry_count", 0),
        "events": [{"event": "verification_completed", "timestamp": _utc_now()}],
    }


def commit_node(state: WorkOnIssueState) -> dict:
    """Stage and commit changes."""
    return {
        "step": "commit",
        "events": [{"event": "commit_completed", "timestamp": _utc_now()}],
    }


def pull_request_node(state: WorkOnIssueState) -> dict:
    """Create or update the pull request."""
    return {
        "step": "pull_request",
        "events": [{"event": "pull_request_completed", "timestamp": _utc_now()}],
    }


def completion_node(state: WorkOnIssueState) -> dict:
    """Mark the workflow as complete."""
    return {
        "step": "completion",
        "status": "completed",
        "events": [{"event": "completion_completed", "timestamp": _utc_now()}],
    }


# ---------------------------------------------------------------------------
# Conditional edge functions
# ---------------------------------------------------------------------------


def route_after_initiate(state: WorkOnIssueState) -> str:
    """Route to ``setup`` if an error is present, otherwise ``planning``."""
    if state.get("error"):
        return "setup"
    return "planning"


def route_after_plan(state: WorkOnIssueState) -> str:
    """Route to ``checklist_creation`` if approved, otherwise ``planning_gate``."""
    if state.get("human_approved"):
        return "checklist_creation"
    return "planning_gate"


def route_after_implementation(state: WorkOnIssueState) -> str:
    """Route to ``implementation_review`` (default path)."""
    return "implementation_review"


def route_after_verify(state: WorkOnIssueState) -> str:
    """Route back to ``implementation`` on retryable error, otherwise ``commit``.

    Caps retry loops at :data:`MAX_RETRIES` to prevent infinite loops.
    """
    if state.get("error") and state.get("retry_count", 0) < MAX_RETRIES:
        return "implementation"
    return "commit"


# ---------------------------------------------------------------------------
# Mermaid diagram helper
# ---------------------------------------------------------------------------


def get_mermaid_diagram() -> str:
    """Build the pilot workflow graph and return its Mermaid diagram string."""
    from .graph_builder import build_work_on_issue_graph

    compiled = build_work_on_issue_graph()
    return compiled.get_graph().draw_mermaid()
