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
import logging
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

logger = logging.getLogger(__name__)

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
    """Construct a :class:`JiraAdapter` from environment variables and config."""
    base_url = os.environ.get("JIRA_BASE_URL", "")
    username = os.environ.get("JIRA_USERNAME", "")
    token = os.environ.get("JIRA_API_TOKEN", "")

    auth_header = base64.b64encode(f"{username}:{token}".encode()).decode()
    headers = {"Authorization": f"Basic {auth_header}", "Content-Type": "application/json"}

    ssl_verify_env = os.environ.get("JIRA_SSL_VERIFY", "")
    ssl_verify = ssl_verify_env.lower() not in ("0", "false") if ssl_verify_env else True

    config = JiraConfig(base_url=base_url, headers=headers, ssl_verify=ssl_verify)
    project_key = platform_config.get("jira", {}).get("project_key", "") or None
    return JiraAdapter(config=config, project_key=project_key)


def _build_github_adapter(platform_config: dict) -> GitHubIssuesAdapter:
    """Construct a :class:`GitHubIssuesAdapter` from platform config."""
    gh = platform_config.get("github", {})
    repo_owner = gh.get("repo_owner", "")
    repo_name = gh.get("repo_name", "")
    repo_slug = f"{repo_owner}/{repo_name}"
    return GitHubIssuesAdapter(repo=repo_slug)
