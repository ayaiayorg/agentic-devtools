"""MCP server implementation for agentic-devtools.

Registers all **implemented** (non-stub) tool adapter functions from
``agentic_devtools/tools/`` as MCP tools using the ``FastMCP`` high-level API.
Config/auth objects are resolved from environment variables at startup.

Usage::

    # Start the server (stdio transport)
    agdt-mcp-server

    # Or programmatically
    from agentic_devtools.mcp import create_mcp_server
    server = create_mcp_server()
    server.run(transport="stdio")
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os

from mcp.server.fastmcp import FastMCP

from agentic_devtools.tools import azure_devops as tools_azure_devops
from agentic_devtools.tools import git as tools_git
from agentic_devtools.tools import jira as tools_jira
from agentic_devtools.tools.jira import JiraConfig

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config loaders
# ---------------------------------------------------------------------------

_JIRA_MISSING_MSG = (
    "Jira is not configured. Set JIRA_BASE_URL and JIRA_API_TOKEN (or JIRA_COPILOT_PAT) environment variables."
)
_AZURE_DEVOPS_MISSING_MSG = (
    "Azure DevOps is not configured. "
    "Set AZURE_DEVOPS_ORG, AZURE_DEVOPS_PROJECT, and AZURE_DEVOPS_PAT "
    "(or AZURE_DEV_OPS_COPILOT_PAT) environment variables."
)


def _load_jira_config() -> JiraConfig | None:
    """Build a :class:`JiraConfig` from environment variables.

    Required:
        - ``JIRA_BASE_URL``
        - ``JIRA_API_TOKEN`` (falls back to ``JIRA_COPILOT_PAT``)

    Optional:
        - ``JIRA_USER_EMAIL`` — when set, Basic auth is used instead of Bearer.
        - ``JIRA_SSL_VERIFY`` — ``"0"``/``"false"`` disables verification;
          any other non-empty string is treated as a CA bundle path.

    Returns ``None`` (with a warning) when required variables are missing.
    """
    base_url = os.environ.get("JIRA_BASE_URL", "")
    # Support both MCP-style and repo-conventional env var names
    token = os.environ.get("JIRA_API_TOKEN", "") or os.environ.get("JIRA_COPILOT_PAT", "")

    if not base_url or not token:
        logger.warning(_JIRA_MISSING_MSG)
        return None

    email = os.environ.get("JIRA_USER_EMAIL", "")
    if email:
        credentials = base64.b64encode(f"{email}:{token}".encode()).decode()
        headers = {"Authorization": f"Basic {credentials}"}
    else:
        headers = {"Authorization": f"Bearer {token}"}

    ssl_env = os.environ.get("JIRA_SSL_VERIFY", "")
    if ssl_env.lower() in ("0", "false"):
        ssl_verify: bool | str = False
    elif ssl_env:
        ssl_verify = ssl_env
    else:
        ssl_verify = True

    return JiraConfig(base_url=base_url, headers=headers, ssl_verify=ssl_verify)


def _load_azure_devops_config() -> tuple | None:
    """Build Azure DevOps config from environment variables.

    Required:
        - ``AZURE_DEVOPS_ORG``
        - ``AZURE_DEVOPS_PROJECT``
        - ``AZURE_DEVOPS_PAT`` (falls back to ``AZURE_DEV_OPS_COPILOT_PAT``,
          then ``AZURE_DEVOPS_EXT_PAT``)

    Optional:
        - ``AZURE_DEVOPS_REPOSITORY`` — repository name. When not set, the
          repository is auto-detected from the git remote URL. If neither
          source provides a repository name, Azure DevOps is treated as
          not configured (returns ``None``).

    Returns a ``(AzureDevOpsConfig, pat, auth_headers)`` tuple, or ``None``
    (with a warning) when required variables are missing or the repository
    cannot be determined.
    """
    from agentic_devtools.cli.azure_devops.config import (
        AzureDevOpsConfig,
        get_repository_name_from_git_remote,
    )

    org = os.environ.get("AZURE_DEVOPS_ORG", "")
    project = os.environ.get("AZURE_DEVOPS_PROJECT", "")
    # Support both MCP-style and repo-conventional env var names
    pat = (
        os.environ.get("AZURE_DEVOPS_PAT", "")
        or os.environ.get("AZURE_DEV_OPS_COPILOT_PAT", "")
        or os.environ.get("AZURE_DEVOPS_EXT_PAT", "")
    )

    if not org or not project or not pat:
        logger.warning(_AZURE_DEVOPS_MISSING_MSG)
        return None

    repository = os.environ.get("AZURE_DEVOPS_REPOSITORY", "")
    if not repository:
        repository = get_repository_name_from_git_remote() or ""

    if not repository:
        logger.warning(
            "Azure DevOps repository could not be determined. "
            "Set AZURE_DEVOPS_REPOSITORY or run from a git repo with an origin remote."
        )
        return None

    config = AzureDevOpsConfig(organization=org, project=project, repository=repository)
    credentials = base64.b64encode(f":{pat}".encode()).decode()
    auth_headers = {"Authorization": f"Basic {credentials}"}

    return (config, pat, auth_headers)


# ---------------------------------------------------------------------------
# Server factory
# ---------------------------------------------------------------------------


def create_mcp_server() -> FastMCP:
    """Create and return a configured :class:`FastMCP` server instance.

    All **implemented** tool adapter functions from ``agentic_devtools/tools/``
    are registered as MCP tools.  Stub functions (those that raise
    :exc:`NotImplementedError`) are excluded.

    Config objects for Jira and Azure DevOps are loaded from environment
    variables once at server creation time and injected into tool handler
    closures.  If a platform's config is missing, its tools are still
    registered but return an error dict when called.
    """
    mcp = FastMCP("agentic-devtools")

    jira_config = _load_jira_config()
    ado_result = _load_azure_devops_config()

    # -- Jira tools --------------------------------------------------------

    @mcp.tool()
    async def jira_create_issue(
        project_key: str,
        summary: str,
        issue_type: str,
        description: str,
        labels: list[str],
        epic_name: str | None = None,
        parent_key: str | None = None,
    ) -> dict:
        """Create a Jira issue.

        Args:
            project_key: Jira project key (e.g. "DFLY").
            summary: Issue summary / title.
            issue_type: Issue type name ("Task", "Epic", "Sub-task", …).
            description: Issue description body.
            labels: Labels to apply.
            epic_name: Epic name field (required when issue_type is "Epic").
            parent_key: Parent issue key (required for "Sub-task").
        """
        if jira_config is None:
            return {"error": _JIRA_MISSING_MSG}
        try:
            result = await asyncio.to_thread(
                tools_jira.create_issue,
                config=jira_config,
                project_key=project_key,
                summary=summary,
                issue_type=issue_type,
                description=description,
                labels=labels,
                epic_name=epic_name,
                parent_key=parent_key,
            )
            return dict(result)
        except Exception as exc:
            logger.exception("Tool call failed")
            return {"error": str(exc)}

    @mcp.tool()
    async def jira_create_epic(
        project_key: str,
        summary: str,
        epic_name: str,
        description: str,
        labels: list[str],
    ) -> dict:
        """Create a Jira Epic.

        Args:
            project_key: Jira project key.
            summary: Epic summary / title.
            epic_name: The Epic Name field value.
            description: Epic description body.
            labels: Labels to apply.
        """
        if jira_config is None:
            return {"error": _JIRA_MISSING_MSG}
        try:
            result = await asyncio.to_thread(
                tools_jira.create_epic,
                config=jira_config,
                project_key=project_key,
                summary=summary,
                epic_name=epic_name,
                description=description,
                labels=labels,
            )
            return dict(result)
        except Exception as exc:
            logger.exception("Tool call failed")
            return {"error": str(exc)}

    @mcp.tool()
    async def jira_create_subtask(
        project_key: str,
        summary: str,
        description: str,
        labels: list[str],
        parent_key: str,
    ) -> dict:
        """Create a Jira Sub-task.

        Args:
            project_key: Jira project key.
            summary: Sub-task summary / title.
            description: Sub-task description body.
            labels: Labels to apply.
            parent_key: Parent issue key.
        """
        if jira_config is None:
            return {"error": _JIRA_MISSING_MSG}
        try:
            result = await asyncio.to_thread(
                tools_jira.create_subtask,
                config=jira_config,
                project_key=project_key,
                summary=summary,
                description=description,
                labels=labels,
                parent_key=parent_key,
            )
            return dict(result)
        except Exception as exc:
            logger.exception("Tool call failed")
            return {"error": str(exc)}

    @mcp.tool()
    async def jira_add_comment(
        issue_key: str,
        comment: str,
    ) -> dict:
        """Add a comment to a Jira issue.

        Args:
            issue_key: The issue key (e.g. "DFLY-1234").
            comment: Comment body text.
        """
        if jira_config is None:
            return {"error": _JIRA_MISSING_MSG}
        try:
            result = await asyncio.to_thread(
                tools_jira.add_comment,
                config=jira_config,
                issue_key=issue_key,
                comment=comment,
            )
            return dict(result)
        except Exception as exc:
            logger.exception("Tool call failed")
            return {"error": str(exc)}

    @mcp.tool()
    async def jira_fetch_issue_context(
        issue_key: str,
    ) -> dict:
        """Fetch full context for a Jira issue including parent and epic.

        Args:
            issue_key: The issue key (e.g. "DFLY-1234").
        """
        if jira_config is None:
            return {"error": _JIRA_MISSING_MSG}
        try:
            result = await asyncio.to_thread(
                tools_jira.fetch_issue_context,
                config=jira_config,
                issue_key=issue_key,
            )
            return dict(result)
        except Exception as exc:
            logger.exception("Tool call failed")
            return {"error": str(exc)}

    # -- Git tools ---------------------------------------------------------

    @mcp.tool()
    async def git_stage_changes(dry_run: bool = False) -> dict:
        """Stage all changes (git add .).

        Args:
            dry_run: Preview without executing.
        """
        try:
            result = await asyncio.to_thread(tools_git.stage_changes, dry_run=dry_run)
            return dict(result)
        except Exception as exc:
            logger.exception("Tool call failed")
            return {"error": str(exc)}

    @mcp.tool()
    async def git_create_commit(message: str, dry_run: bool = False) -> dict:
        """Create a new commit with the given message.

        Args:
            message: Commit message.
            dry_run: Preview without executing.
        """
        try:
            result = await asyncio.to_thread(tools_git.create_commit, message=message, dry_run=dry_run)
            return dict(result)
        except Exception as exc:
            logger.exception("Tool call failed")
            return {"error": str(exc)}

    @mcp.tool()
    async def git_amend_commit(message: str, dry_run: bool = False) -> dict:
        """Amend the current commit with a new message.

        Args:
            message: New commit message.
            dry_run: Preview without executing.
        """
        try:
            result = await asyncio.to_thread(tools_git.amend_commit, message=message, dry_run=dry_run)
            return dict(result)
        except Exception as exc:
            logger.exception("Tool call failed")
            return {"error": str(exc)}

    @mcp.tool()
    async def git_push(dry_run: bool = False) -> dict:
        """Push to remote (regular push).

        Args:
            dry_run: Preview without executing.
        """
        try:
            result = await asyncio.to_thread(tools_git.push, dry_run=dry_run)
            return dict(result)
        except Exception as exc:
            logger.exception("Tool call failed")
            return {"error": str(exc)}

    @mcp.tool()
    async def git_force_push(dry_run: bool = False) -> dict:
        """Force push with lease.

        Args:
            dry_run: Preview without executing.
        """
        try:
            result = await asyncio.to_thread(tools_git.force_push, dry_run=dry_run)
            return dict(result)
        except Exception as exc:
            logger.exception("Tool call failed")
            return {"error": str(exc)}

    @mcp.tool()
    async def git_publish_branch(dry_run: bool = False) -> dict:
        """Push and set upstream for the current branch.

        Args:
            dry_run: Preview without executing.
        """
        try:
            result = await asyncio.to_thread(tools_git.publish_branch, dry_run=dry_run)
            return dict(result)
        except Exception as exc:
            logger.exception("Tool call failed")
            return {"error": str(exc)}

    @mcp.tool()
    async def git_save_work(
        commit_message: str,
        amend: bool = False,
        skip_stage: bool = False,
        skip_push: bool = False,
        dry_run: bool = False,
    ) -> dict:
        """Stage, commit, and push changes in one operation.

        Args:
            commit_message: The commit message.
            amend: If True, amend the existing commit.
            skip_stage: If True, skip the staging step.
            skip_push: If True, skip the push step.
            dry_run: Preview without executing.
        """
        try:
            result = await asyncio.to_thread(
                tools_git.save_work,
                commit_message=commit_message,
                amend=amend,
                skip_stage=skip_stage,
                skip_push=skip_push,
                dry_run=dry_run,
            )
            return dict(result)
        except Exception as exc:
            logger.exception("Tool call failed")
            return {"error": str(exc)}

    @mcp.tool()
    async def git_get_recent_changes(num_commits: int = 10) -> dict:
        """Return recent commits from the current branch.

        Args:
            num_commits: Maximum number of commits to return.
        """
        try:
            result = await asyncio.to_thread(tools_git.get_recent_changes, num_commits=num_commits)
            return dict(result)
        except Exception as exc:
            logger.exception("Tool call failed")
            return {"error": str(exc)}

    # -- Azure DevOps tools ------------------------------------------------

    @mcp.tool()
    async def azure_devops_create_pull_request(
        source_branch: str,
        title: str,
        target_branch: str = "main",
        description: str | None = None,
        draft: bool = True,
    ) -> dict:
        """Create an Azure DevOps pull request.

        Args:
            source_branch: Source branch name.
            title: PR title.
            target_branch: Target branch name (default "main").
            description: Optional PR description.
            draft: Whether to create the PR as a draft.
        """
        if ado_result is None:
            return {"error": _AZURE_DEVOPS_MISSING_MSG}
        try:
            config, pat, _headers = ado_result
            result = await asyncio.to_thread(
                tools_azure_devops.create_pull_request,
                config=config,
                pat=pat,
                source_branch=source_branch,
                title=title,
                target_branch=target_branch,
                description=description,
                draft=draft,
            )
            return dict(result)
        except Exception as exc:
            logger.exception("Tool call failed")
            return {"error": str(exc)}

    @mcp.tool()
    async def azure_devops_reply_to_thread(
        pull_request_id: int,
        thread_id: int,
        content: str,
        resolve_thread: bool = False,
    ) -> dict:
        """Reply to an existing PR comment thread.

        Args:
            pull_request_id: The PR ID.
            thread_id: The thread to reply to.
            content: Reply content.
            resolve_thread: If True, resolve the thread after replying.
        """
        if ado_result is None:
            return {"error": _AZURE_DEVOPS_MISSING_MSG}
        try:
            config, pat, _headers = ado_result
            result = await asyncio.to_thread(
                tools_azure_devops.reply_to_pull_request_thread,
                config=config,
                pat=pat,
                pull_request_id=pull_request_id,
                thread_id=thread_id,
                content=content,
                resolve_thread=resolve_thread,
            )
            return dict(result)
        except Exception as exc:
            logger.exception("Tool call failed")
            return {"error": str(exc)}

    @mcp.tool()
    async def azure_devops_add_comment(
        pull_request_id: int,
        content: str,
        path: str | None = None,
        line: int | None = None,
        end_line: int | None = None,
        resolve_after_posting: bool = True,
    ) -> dict:
        """Add a new comment thread to a pull request.

        Args:
            pull_request_id: The PR ID.
            content: Comment content.
            path: Optional file path for file-level comments.
            line: Optional start line number.
            end_line: Optional end line number.
            resolve_after_posting: If True, resolve the thread after posting.
        """
        if ado_result is None:
            return {"error": _AZURE_DEVOPS_MISSING_MSG}
        try:
            config, pat, _headers = ado_result
            result = await asyncio.to_thread(
                tools_azure_devops.add_pull_request_comment,
                config=config,
                pat=pat,
                pull_request_id=pull_request_id,
                content=content,
                path=path,
                line=line,
                end_line=end_line,
                resolve_after_posting=resolve_after_posting,
            )
            return dict(result)
        except Exception as exc:
            logger.exception("Tool call failed")
            return {"error": str(exc)}

    @mcp.tool()
    async def azure_devops_update_review_narrative(
        pull_request_id: int,
        content: str,
    ) -> dict:
        """Update the review narrative in the overall PR summary comment.

        Args:
            pull_request_id: The PR ID.
            content: New narrative content.
        """
        if ado_result is None:
            return {"error": _AZURE_DEVOPS_MISSING_MSG}
        try:
            config, pat, _headers = ado_result
            result = await asyncio.to_thread(
                tools_azure_devops.update_review_narrative,
                config=config,
                pat=pat,
                pull_request_id=pull_request_id,
                content=content,
            )
            return dict(result)
        except Exception as exc:
            logger.exception("Tool call failed")
            return {"error": str(exc)}

    return mcp


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Start the AGDT MCP server (stdio transport)."""
    server = create_mcp_server()
    server.run(transport="stdio")


if __name__ == "__main__":  # pragma: no cover
    main()
