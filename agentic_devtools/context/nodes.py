"""Async LangGraph-compatible node functions for context retrieval."""

from __future__ import annotations

import base64
import logging
import os
from datetime import datetime, timezone

from agentic_devtools.cli.workflows.preflight import get_git_repo_root
from agentic_devtools.orchestration.state_schema import WorkOnIssueState
from agentic_devtools.tools.jira import JiraConfig

from .retriever import IssueContextRetriever

logger = logging.getLogger(__name__)


def _utc_now() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _build_jira_config() -> JiraConfig:
    """Construct a :class:`JiraConfig` from environment variables.

    This helper is intentionally permissive and always returns a
    :class:`JiraConfig` instance, even when typical "required" values
    such as base URL, token, or identity are missing. It reads:

    * ``JIRA_BASE_URL`` for the base URL (default: empty string)
    * ``JIRA_API_TOKEN`` or ``JIRA_COPILOT_PAT`` for the token
    * ``JIRA_USER_EMAIL``, ``JIRA_EMAIL``, or ``JIRA_USERNAME`` for the
      user identity
    * ``JIRA_AUTH_SCHEME`` to decide how to build the ``Authorization``
      header (default: ``"bearer"``)

    Authorization header behavior:

    * If ``JIRA_AUTH_SCHEME`` is ``"basic"`` (case-insensitive) and both
      an identity and token are present, it sets
      ``Authorization: Basic <base64(email:token)>``.
    * If ``JIRA_AUTH_SCHEME`` is not ``"basic"`` and a token is present,
      it sets ``Authorization: Bearer <token>``.
    * Otherwise, no ``Authorization`` header is set and authentication
      failures will surface later at call time.

    SSL verification honours ``JIRA_SSL_VERIFY``, then falls back to
    ``JIRA_CA_BUNDLE`` / ``REQUESTS_CA_BUNDLE`` (same env vars used by
    the CLI helpers and the adapter builder):

    * ``JIRA_SSL_VERIFY="0"`` or ``"false"`` → disabled (``False``).
    * ``JIRA_SSL_VERIFY`` set to any other non-empty value → CA bundle path.
    * ``JIRA_CA_BUNDLE`` or ``REQUESTS_CA_BUNDLE`` set → CA bundle path.
    * Nothing set → strict verification (``True``).

    Unlike the stricter
    :func:`agentic_devtools.mcp.server._load_jira_config`, this function
    does not return ``None`` when configuration is incomplete; callers
    should perform any additional validation they require.
    """
    base_url = os.environ.get("JIRA_BASE_URL", "")
    token = os.environ.get("JIRA_API_TOKEN", "") or os.environ.get("JIRA_COPILOT_PAT", "")
    email = (
        os.environ.get("JIRA_USER_EMAIL", "") or os.environ.get("JIRA_EMAIL", "") or os.environ.get("JIRA_USERNAME", "")
    )
    auth_scheme = os.environ.get("JIRA_AUTH_SCHEME", "bearer").lower()

    headers: dict[str, str] = {}
    if email or auth_scheme == "basic":
        # Basic auth: use email:token credentials when identity is available
        if email and token:
            credentials = base64.b64encode(f"{email}:{token}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"
        # else: no Authorization header — will fail lazily at call time
    elif token:
        headers["Authorization"] = f"Bearer {token}"

    ssl_env = os.environ.get("JIRA_SSL_VERIFY", "")
    ssl_verify: bool | str
    if ssl_env.lower() in ("0", "false"):
        ssl_verify = False
    elif ssl_env:
        ssl_verify = ssl_env
    else:
        # Fall back to CA bundle env vars used by cli/jira/helpers._get_ssl_verify
        ca_bundle = os.environ.get("JIRA_CA_BUNDLE", "") or os.environ.get("REQUESTS_CA_BUNDLE", "")
        ssl_verify = ca_bundle if ca_bundle else True

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
    repo_path = get_git_repo_root() or os.getcwd()

    retriever = IssueContextRetriever(jira_config=jira_config, repo_path=repo_path)
    context = await retriever.retrieve(issue_key, affected_paths)

    return {
        "agent_context": context.to_dict(),
        "events": [{"event": "context_retrieval_completed", "timestamp": _utc_now()}],
        "error": None,
    }
