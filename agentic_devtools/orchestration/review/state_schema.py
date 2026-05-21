"""LangGraph state schema for the PR review workflow."""

import operator
from typing import Annotated, TypedDict


class PRReviewState(TypedDict, total=False):
    """State schema for the LangGraph PR review workflow.

    Uses LangGraph's Annotated channel pattern:
    - ``events`` uses ``operator.add`` reducer for append-only logging.
    - ``review_comments`` uses ``operator.add`` for append-only collection.
    - All other fields use default last-writer-wins semantics.
    """

    # Input fields
    pr_id: int
    state_dir: str
    config: dict

    # Workflow tracking
    step: str
    status: str
    error: str | None

    # PR details populated by fetch node
    pr_title: str
    pr_description: str
    source_branch: str
    target_branch: str
    changed_files: list[str]

    # Review output
    review_comments: Annotated[list[dict], operator.add]
    review_summary: str
    decision: str  # "approved" | "needs-work"

    # Audit trail
    events: Annotated[list[dict], operator.add]
