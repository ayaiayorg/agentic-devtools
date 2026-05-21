"""Runner for the LangGraph PR review workflow.

Orchestrates graph invocation, session recording, and error handling.
"""

from __future__ import annotations

import datetime
import logging
import uuid

from .graph_builder import build_pr_review_graph

logger = logging.getLogger("[langchain]")


def run_langchain_review(
    pr_id: int,
    config: dict | None = None,
    state_dir: str | None = None,
) -> dict:
    """Run the LangGraph-based PR review pipeline.

    Orchestrates:
    1. Build or retrieve the compiled review graph
    2. Invoke with initial state
    3. Record session in review-state.json
    4. Return final graph state

    Args:
        pr_id: The pull request ID to review.
        config: Optional configuration dict (model settings, etc.).
        state_dir: Path to the state directory for artifact storage.

    Returns:
        The final graph state dict after completion.

    Raises:
        SystemExit: If the graph invocation fails fatally.
    """
    import sys

    session_id = uuid.uuid4().hex
    started_utc = _now()
    model_id = (config or {}).get("model")

    logger.info("[langchain] Starting LangGraph review for PR #%d (session: %s)", pr_id, session_id[:8])

    # Build the graph
    graph = build_pr_review_graph()

    # Prepare initial state
    initial_state: dict = {
        "pr_id": pr_id,
        "state_dir": state_dir or "",
        "config": config or {},
        "step": "init",
        "status": "active",
        "review_comments": [],
        "events": [{"event": "langchain_review_started", "timestamp": started_utc}],
    }

    # Invoke the graph
    try:
        final_state = graph.invoke(initial_state)
    except Exception as e:
        logger.exception("[langchain] Graph invocation failed: %s", e)
        _record_failed_session(pr_id, session_id, started_utc, str(e), model_id=model_id)
        print(f"ERROR: LangChain review failed: {e}", file=sys.stderr)
        sys.exit(1)

    if final_state.get("status") == "failed":
        error = str(final_state.get("error", "Unknown review failure"))
        logger.error("[langchain] Review failed: %s", error)
        _record_failed_session(pr_id, session_id, started_utc, error, model_id=model_id)
        print(f"ERROR: LangChain review failed: {error}", file=sys.stderr)
        sys.exit(1)

    # Record successful session
    _record_session(pr_id, session_id, started_utc, final_state)

    logger.info("[langchain] Review complete. Decision: %s", final_state.get("decision", "unknown"))
    return final_state


def _record_session(
    pr_id: int,
    session_id: str,
    started_utc: str,
    final_state: dict,
) -> None:
    """Record a completed review session in review-state.json."""
    try:
        from agentic_devtools.cli.azure_devops.review_state import (
            ReviewSession,
            load_review_state,
            save_review_state,
        )

        review_state = load_review_state(pr_id)
        if review_state:
            resolved_model_id = (
                final_state.get("model_id")
                or final_state.get("model")
                or final_state.get("config", {}).get("model")
                or "unknown"
            )
            session = ReviewSession(
                sessionId=session_id,
                modelId=str(resolved_model_id),
                startedUtc=started_utc,
                completedUtc=_now(),
                status=final_state.get("status", "completed"),
                engine="langchain",
            )
            review_state.sessions.append(session)
            save_review_state(review_state)
            logger.info("[langchain] Session recorded: %s", session_id[:8])
    except Exception as e:
        # Non-fatal: session recording failure shouldn't block the review
        logger.warning("[langchain] Failed to record session: %s", e)


def _record_failed_session(
    pr_id: int,
    session_id: str,
    started_utc: str,
    error: str,
    model_id: str | None = None,
) -> None:
    """Record a failed review session in review-state.json."""
    try:
        from agentic_devtools.cli.azure_devops.review_state import (
            ReviewSession,
            load_review_state,
            save_review_state,
        )

        review_state = load_review_state(pr_id)
        if review_state:
            session = ReviewSession(
                sessionId=session_id,
                modelId=model_id or "unknown",
                startedUtc=started_utc,
                completedUtc=_now(),
                status="failed",
                engine="langchain",
            )
            review_state.sessions.append(session)
            save_review_state(review_state)
            logger.warning("[langchain] Recorded failed session %s: %s", session_id[:8], error)
        else:
            logger.warning("[langchain] Failed session not recorded for PR #%d: %s", pr_id, error)
    except Exception as e:
        logger.warning("[langchain] Failed to record failed session: %s", e)


def _now() -> str:
    """Return current UTC timestamp as ISO-8601 string."""
    return datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
