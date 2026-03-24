"""LangGraph state schema definitions for AGDT orchestration workflows."""

import operator
from typing import Annotated, TypedDict


class WorkOnIssueEvent(TypedDict):
    """A single event entry in the workflow audit trail."""

    event: str
    timestamp: str


class WorkOnIssueState(TypedDict, total=False):
    """State schema for the work-on-jira-issue workflow.

    Uses LangGraph's Annotated channel pattern:
    - ``events`` uses ``operator.add`` reducer for append-only logging.
    - All other fields use default last-writer-wins semantics.

    Since ``TypedDict`` does not support default values, node functions
    must use ``.get()`` to handle missing keys gracefully.
    """

    issue_key: str
    step: str
    status: str
    plan: str
    error: str | None
    retry_count: int
    events: Annotated[list[WorkOnIssueEvent], operator.add]
    human_approved: bool
    agent_context: dict
    affected_paths: list[str]
