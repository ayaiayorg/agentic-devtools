"""Node functions for the LangGraph PR review workflow.

Each node receives the current graph state and returns a partial state update.
Nodes delegate to existing agentic_devtools infrastructure where possible.
"""

from __future__ import annotations

import datetime
import logging

logger = logging.getLogger("[langchain]")


def fetch_pr_details_node(state: dict) -> dict:
    """Fetch PR details from Azure DevOps.

    Retrieves the PR metadata (title, description, branch info, changed files)
    and stores them in the graph state for downstream nodes.
    """
    logger.info("Fetching PR details for PR #%s...", state.get("pr_id"))

    pr_id = state.get("pr_id")
    if not pr_id:
        return {
            "step": "fetch_pr_details",
            "status": "failed",
            "error": "No pr_id provided in state",
            "events": [{"event": "fetch_pr_details_failed", "timestamp": _now()}],
        }

    # Delegate to existing infrastructure for fetching PR details
    try:
        from agentic_devtools.cli.azure_devops.helpers import (
            get_pull_request_changed_files,
            get_pull_request_details,
        )

        details = get_pull_request_details(pr_id)
    except Exception as e:
        logger.exception("Failed to fetch PR details: %s", e)
        return {
            "step": "fetch_pr_details",
            "status": "failed",
            "error": f"Failed to fetch PR details: {e}",
            "events": [{"event": "fetch_pr_details_failed", "timestamp": _now()}],
        }

    if not details:
        return {
            "step": "fetch_pr_details",
            "status": "failed",
            "error": f"PR #{pr_id} not found or not accessible",
            "events": [{"event": "fetch_pr_details_failed", "timestamp": _now()}],
        }

    changes = details.get("changes", [])
    changed_files = []
    for change in changes:
        path = change.get("item", {}).get("path", "")
        if path:
            changed_files.append(path)
    if not changed_files:
        changed_files = get_pull_request_changed_files(pr_id) or []

    if not changed_files:
        return {
            "step": "fetch_pr_details",
            "status": "failed",
            "error": ("Changed files are not available from pull request details or latest iteration changes."),
            "events": [{"event": "fetch_pr_details_failed", "timestamp": _now()}],
        }

    return {
        "step": "fetch_pr_details",
        "status": "active",
        "pr_title": details.get("title", ""),
        "pr_description": details.get("description", ""),
        "source_branch": details.get("sourceRefName", "").replace("refs/heads/", ""),
        "target_branch": details.get("targetRefName", "").replace("refs/heads/", ""),
        "changed_files": changed_files,
        "events": [{"event": "fetch_pr_details_complete", "timestamp": _now()}],
    }


def scaffold_node(state: dict) -> dict:
    """Record scaffold progress for the LangGraph workflow.

    This node currently emits workflow events only. Review-state creation and
    Azure DevOps thread scaffolding are handled by the existing review command
    flow outside this node.
    """
    logger.info("Scaffolding review for PR #%s...", state.get("pr_id"))

    return {
        "step": "scaffold",
        "status": "active",
        "events": [{"event": "scaffold_complete", "timestamp": _now()}],
    }


def review_file_node(state: dict) -> dict:
    """Review changed files and produce review comments.

    Iterates over the changed files list and generates review comments
    for each file.
    """
    changed_files = state.get("changed_files", [])
    num_files = len(changed_files)
    logger.info("Reviewing %d file(s)...", num_files)

    # Generate placeholder review output — actual LLM-based review
    # will be wired in subsequent iterations
    comments: list[dict] = []
    for i, file_path in enumerate(changed_files, 1):
        logger.info("[langchain] reviewing file %d/%d: %s", i, num_files, file_path)
        comments.append(
            {
                "file": file_path,
                "status": "reviewed",
                "comments": [],
            }
        )

    return {
        "step": "review_files",
        "status": "active",
        "review_comments": comments,
        "events": [{"event": "review_files_complete", "timestamp": _now()}],
    }


def summarize_node(state: dict) -> dict:
    """Summarize review findings and determine overall decision.

    Aggregates file-level review comments into a summary and decides
    whether to approve or request changes.
    """
    logger.info("Summarizing review...")

    comments = state.get("review_comments", [])
    has_issues = any(c.get("comments") for c in comments if isinstance(c, dict))
    review_ready_for_approval = bool(state.get("review_ready_for_approval", False))

    decision = "needs-work" if has_issues or not review_ready_for_approval else "approved"
    summary = f"Reviewed {len(comments)} file(s). Decision: {decision}."

    return {
        "step": "summarize",
        "status": "active",
        "review_summary": summary,
        "decision": decision,
        "events": [{"event": "summarize_complete", "timestamp": _now()}],
    }


def complete_node(state: dict) -> dict:
    """Mark the review workflow as complete.

    Finalizes the review session and records completion status.
    """
    logger.info("Review complete. Decision: %s", state.get("decision", "unknown"))

    return {
        "step": "completion",
        "status": "completed",
        "events": [{"event": "review_complete", "timestamp": _now()}],
    }


def _now() -> str:
    """Return current UTC timestamp as ISO-8601 string."""
    return datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
