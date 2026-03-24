"""Pluggable issue adapter package.

Public API
----------
- :class:`IssueAdapter` — abstract base class
- :class:`JiraAdapter`, :class:`GitHubIssuesAdapter`, :class:`MarkdownAdapter` — concrete adapters
- :func:`get_adapter` — factory that returns the correct adapter based on platform config
- Shared TypedDicts: :class:`IssueResult`, :class:`IssueDetail`, :class:`CommentResult`,
  :class:`IssueSummary`, :class:`IssueFilters`, :class:`Comment`
"""

from __future__ import annotations

import base64
import os

from agentic_devtools.adapters.base import (
    Comment,
    CommentResult,
    IssueAdapter,
    IssueDetail,
    IssueFilters,
    IssueResult,
    IssueSummary,
)
from agentic_devtools.adapters.github_adapter import GitHubIssuesAdapter
from agentic_devtools.adapters.jira_adapter import JiraAdapter
from agentic_devtools.adapters.markdown_adapter import MarkdownAdapter
from agentic_devtools.config import load_platform_config
from agentic_devtools.tools.jira import JiraConfig

__all__ = [
    "Comment",
    "CommentResult",
    "GitHubIssuesAdapter",
    "IssueAdapter",
    "IssueDetail",
    "IssueFilters",
    "IssueResult",
    "IssueSummary",
    "JiraAdapter",
    "MarkdownAdapter",
    "get_adapter",
]


def get_adapter(repo_path: str) -> IssueAdapter:
    """Return an :class:`IssueAdapter` based on the platform configuration.

    Reads ``load_platform_config(repo_path)["issue_adapter"]`` and returns
    the matching adapter instance.  Adapter construction is eager but
    connectivity is validated lazily (adapter methods raise on failure).

    Args:
        repo_path: Absolute (or relative) path to the target repository root.

    Returns:
        A concrete :class:`IssueAdapter` instance.

    Raises:
        ValueError: If the configured adapter name is not recognised.
    """
    platform_config = load_platform_config(repo_path)
    adapter_name = platform_config["issue_adapter"]

    if adapter_name == "jira":
        return _build_jira_adapter(platform_config)

    if adapter_name == "github":
        return _build_github_adapter(platform_config)

    if adapter_name == "markdown":
        return MarkdownAdapter(repo_path=repo_path)

    raise ValueError(f"Unknown issue adapter: {adapter_name}")


# ------------------------------------------------------------------
# Private builder helpers
# ------------------------------------------------------------------


def _build_jira_adapter(platform_config: dict) -> JiraAdapter:
    """Construct a :class:`JiraAdapter` from environment variables and config.

    Authentication follows the same conventions as
    :func:`agentic_devtools.mcp.server._load_jira_config`:

    * **Token** — ``JIRA_API_TOKEN`` falling back to ``JIRA_COPILOT_PAT``.
    * **Identity** — ``JIRA_USER_EMAIL`` → ``JIRA_EMAIL`` → ``JIRA_USERNAME``.
    * **Scheme** — ``JIRA_AUTH_SCHEME`` (default ``"bearer"``).  When the
      scheme is ``"basic"`` **or** an identity env var is set, Basic auth is
      attempted: the ``Authorization`` header is only added when **both**
      identity and token are present; otherwise no auth header is sent and
      the request will fail lazily at call time.  In all other cases, when a
      token is available, Bearer auth is used.

    SSL verification honours ``JIRA_SSL_VERIFY``, then falls back to
    ``JIRA_CA_BUNDLE`` / ``REQUESTS_CA_BUNDLE`` (same env vars used by the
    CLI helpers):

    * ``JIRA_SSL_VERIFY="0"`` or ``"false"`` → disabled (``False``).
    * ``JIRA_SSL_VERIFY`` set to any other non-empty value → CA bundle path.
    * ``JIRA_CA_BUNDLE`` or ``REQUESTS_CA_BUNDLE`` set → CA bundle path.
    * Nothing set → strict verification (``True``).
    """
    base_url = os.environ.get("JIRA_BASE_URL", "")
    token = os.environ.get("JIRA_API_TOKEN", "") or os.environ.get("JIRA_COPILOT_PAT", "")
    identity = (
        os.environ.get("JIRA_USER_EMAIL", "")
        or os.environ.get("JIRA_EMAIL", "")
        or os.environ.get("JIRA_USERNAME", "")
    )
    auth_scheme = os.environ.get("JIRA_AUTH_SCHEME", "bearer").lower()

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if identity or auth_scheme == "basic":
        if identity and token:
            credentials = base64.b64encode(f"{identity}:{token}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"
        # else: no Authorization header — will fail lazily at call time
    elif token:
        headers["Authorization"] = f"Bearer {token}"

    ssl_env = os.environ.get("JIRA_SSL_VERIFY", "")
    ssl_verify: bool | str
    if ssl_env.lower() in ("0", "false"):
        ssl_verify = False
    elif ssl_env:
        ssl_verify = ssl_env  # CA bundle path
    else:
        # Fall back to CA bundle env vars used by cli/jira/helpers._get_ssl_verify
        ca_bundle = os.environ.get("JIRA_CA_BUNDLE", "") or os.environ.get("REQUESTS_CA_BUNDLE", "")
        ssl_verify = ca_bundle if ca_bundle else True

    config = JiraConfig(base_url=base_url, headers=headers, ssl_verify=ssl_verify)
    project_key = platform_config.get("jira", {}).get("project_key", "") or None
    return JiraAdapter(config=config, project_key=project_key)


def _build_github_adapter(platform_config: dict) -> GitHubIssuesAdapter:
    """Construct a :class:`GitHubIssuesAdapter` from platform config."""
    gh = platform_config.get("github", {})
    repo_owner = gh.get("repo_owner", "")
    repo_name = gh.get("repo_name", "")
    repo_slug = f"{repo_owner}/{repo_name}" if repo_owner and repo_name else ""
    return GitHubIssuesAdapter(repo=repo_slug)
