"""Async LangGraph-compatible node functions for context retrieval."""

from __future__ import annotations

import base64
import logging
import os
from datetime import datetime, timezone

from agentic_devtools.orchestration.state_schema import WorkOnIssueState
from agentic_devtools.tools.jira import JiraConfig

from .retriever import IssueContextRetriever

logger = logging.getLogger(__name__)


def _utc_now() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _build_jira_config() -> JiraConfig:
    """Construct a :class:`JiraConfig` from environment variables.

    Uses the same env-var convention as
    :func:`agentic_devtools.mcp.server._load_jira_config`.
    """
    base_url = os.environ.get("JIRA_BASE_URL", "")
    token = os.environ.get("JIRA_API_TOKEN", "") or os.environ.get("JIRA_COPILOT_PAT", "")
    email = (
        os.environ.get("JIRA_USER_EMAIL", "") or os.environ.get("JIRA_EMAIL", "") or os.environ.get("JIRA_USERNAME", "")
    )

    headers: dict[str, str] = {}
    if email and token:
        credentials = base64.b64encode(f"{email}:{token}".encode()).decode()
        headers["Authorization"] = f"Basic {credentials}"
    elif token:
        headers["Authorization"] = f"Bearer {token}"

    ssl_env = os.environ.get("JIRA_SSL_VERIFY", "")
    ssl_verify: bool | str
    if ssl_env.lower() in ("0", "false"):
        ssl_verify = False
    elif ssl_env:
        ssl_verify = ssl_env
    else:
        ssl_verify = True

    return JiraConfig(base_url=base_url, headers=headers, ssl_verify=ssl_verify)


async def retrieve_context_node(state: WorkOnIssueState) -> dict:
    """LangGraph node that retrieves and aggregates project context.

    Reads ``issue_key`` and ``affected_paths`` from *state*, constructs a
    :class:`JiraConfig` from environment variables, and delegates to
    :class:`IssueContextRetriever`.

    Returns a dict suitable for merging back into ``WorkOnIssueState``.
    """
    issue_key = state.get("issue_key")  # type: ignore[arg-type]
    if not issue_key:
        return {
            "agent_context": {},
            "error": "issue_key is required for context retrieval",
            "events": [{"event": "context_retrieval_failed", "timestamp": _utc_now()}],
        }

    affected_paths: list[str] = state.get("affected_paths", [])  # type: ignore[arg-type]
    jira_config = _build_jira_config()
    repo_path = os.getcwd()

    retriever = IssueContextRetriever(jira_config=jira_config, repo_path=repo_path)
    context = await retriever.retrieve(issue_key, affected_paths)

    return {
        "agent_context": context.to_dict(),
        "events": [{"event": "context_retrieval_completed", "timestamp": _utc_now()}],
    }
