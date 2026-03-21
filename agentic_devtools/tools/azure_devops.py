"""Azure DevOps tool adapter functions.

Stateless, typed functions for Azure DevOps operations. Each function
accepts an ``AzureDevOpsConfig`` (from
``agentic_devtools.cli.azure_devops.config``) plus explicit auth
parameters and returns a ``TypedDict`` result.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from typing_extensions import TypedDict

if TYPE_CHECKING:
    from agentic_devtools.cli.azure_devops.config import AzureDevOpsConfig

# ---------------------------------------------------------------------------
# Result TypedDicts
# ---------------------------------------------------------------------------


class CreatePullRequestResult(TypedDict):
    """Result of creating a pull request."""

    pull_request_id: int
    url: str
    raw_output: str


class ReplyToThreadResult(TypedDict):
    """Result of replying to a PR comment thread."""

    comment_id: int
    thread_resolved: bool


class AddCommentResult(TypedDict):
    """Result of adding a comment to a PR."""

    thread_id: int
    comment_id: int


class UpdateNarrativeResult(TypedDict):
    """Result of updating the review narrative."""

    success: bool
    message: str


class AddReviewerResult(TypedDict):
    """Result of adding a reviewer to a PR (not yet implemented)."""

    success: bool
    message: str


class CompletePullRequestResult(TypedDict):
    """Result of completing a pull request (not yet implemented)."""

    success: bool
    message: str


class FileReviewResult(TypedDict):
    """Result of a file review operation (not yet implemented)."""

    success: bool
    message: str


# ---------------------------------------------------------------------------
# Tool functions
# ---------------------------------------------------------------------------


def create_pull_request(
    config: AzureDevOpsConfig,
    pat: str,
    source_branch: str,
    title: str,
    target_branch: str = "main",
    description: str | None = None,
    draft: bool = True,
) -> CreatePullRequestResult:
    """Create a pull request using the Azure CLI.

    Args:
        config: An :class:`~agentic_devtools.cli.azure_devops.config.AzureDevOpsConfig`.
        pat: Azure DevOps Personal Access Token.
        source_branch: Source branch name.
        title: PR title.
        target_branch: Target branch name (default ``"main"``).
        description: Optional PR description.
        draft: Whether to create the PR as a draft.

    Returns:
        A :class:`CreatePullRequestResult`.

    Raises:
        RuntimeError: If the ``az`` CLI command fails.
    """
    from agentic_devtools.cli.azure_devops.helpers import parse_json_response
    from agentic_devtools.cli.subprocess_utils import run_safe

    env = os.environ.copy()
    env["AZURE_DEVOPS_EXT_PAT"] = pat

    cmd = [
        "az",
        "repos",
        "pr",
        "create",
        "--source-branch",
        source_branch,
        "--target-branch",
        target_branch,
        "--title",
        title,
        "--organization",
        config.organization,
        "--project",
        config.project,
        "--repository",
        config.repository,
        "--output",
        "json",
    ]

    if draft:
        cmd.append("--draft")

    if description:
        cmd.extend(["--description", description])

    result = run_safe(cmd, capture_output=True, text=True, env=env)

    if result.returncode != 0:
        raise RuntimeError(f"az repos pr create failed: {result.stderr}")

    pr_data = parse_json_response(result.stdout, "PR response")
    pull_request_id = pr_data.get("pullRequestId", 0)

    repo_web_url = pr_data.get("repository", {}).get("webUrl", "")
    pr_url = f"{repo_web_url}/pullrequest/{pull_request_id}" if repo_web_url else ""

    return CreatePullRequestResult(
        pull_request_id=pull_request_id,
        url=pr_url,
        raw_output=result.stdout,
    )


def reply_to_pull_request_thread(
    config: AzureDevOpsConfig,
    pat: str,
    pull_request_id: int,
    thread_id: int,
    content: str,
    resolve_thread: bool = False,
) -> ReplyToThreadResult:
    """Reply to an existing PR comment thread.

    Args:
        config: An :class:`~agentic_devtools.cli.azure_devops.config.AzureDevOpsConfig`.
        pat: Azure DevOps Personal Access Token.
        pull_request_id: The PR ID.
        thread_id: The thread to reply to.
        content: Reply content.
        resolve_thread: If *True*, resolve the thread after replying.

    Returns:
        A :class:`ReplyToThreadResult`.
    """
    from agentic_devtools.cli.azure_devops.auth import get_auth_headers
    from agentic_devtools.cli.azure_devops.helpers import (
        get_repository_id,
        require_requests,
        resolve_thread_by_id,
    )

    requests = require_requests()
    headers = get_auth_headers(pat)
    repo_id = get_repository_id(config.organization, config.project, config.repository)

    comment_url = config.build_api_url(repo_id, "pullRequests", pull_request_id, "threads", thread_id, "comments")
    comment_body: dict[str, Any] = {
        "content": content,
        "commentType": "text",
    }

    response = requests.post(comment_url, headers=headers, json=comment_body, timeout=30)
    response.raise_for_status()

    result = response.json()
    comment_id = result.get("id", 0)

    thread_resolved = False
    if resolve_thread:
        resolve_thread_by_id(
            requests,
            headers,
            config,
            repo_id,
            pull_request_id,
            thread_id,
            status="fixed",
        )
        thread_resolved = True

    return ReplyToThreadResult(
        comment_id=comment_id,
        thread_resolved=thread_resolved,
    )


def add_pull_request_comment(
    config: AzureDevOpsConfig,
    pat: str,
    pull_request_id: int,
    content: str,
    path: str | None = None,
    line: int | None = None,
    end_line: int | None = None,
    resolve_after_posting: bool = True,
) -> AddCommentResult:
    """Add a new comment thread to a pull request.

    Args:
        config: An :class:`~agentic_devtools.cli.azure_devops.config.AzureDevOpsConfig`.
        pat: Azure DevOps Personal Access Token.
        pull_request_id: The PR ID.
        content: Comment content.
        path: Optional file path for file-level comments.
        line: Optional start line number.
        end_line: Optional end line number.
        resolve_after_posting: If *True* (default), resolve the thread
            immediately after posting.

    Returns:
        An :class:`AddCommentResult`.
    """
    from agentic_devtools.cli.azure_devops.auth import get_auth_headers
    from agentic_devtools.cli.azure_devops.helpers import (
        build_thread_context,
        get_repository_id,
        require_requests,
        resolve_thread_by_id,
    )

    requests = require_requests()
    headers = get_auth_headers(pat)
    repo_id = get_repository_id(config.organization, config.project, config.repository)

    thread_context = build_thread_context(path, line, end_line)

    thread_url = config.build_api_url(repo_id, "pullRequests", pull_request_id, "threads")

    thread_body: dict[str, Any] = {
        "comments": [
            {
                "content": content,
                "commentType": "text",
            }
        ],
        "status": "active",
    }

    if thread_context:
        thread_body["threadContext"] = thread_context

    response = requests.post(thread_url, headers=headers, json=thread_body, timeout=30)
    response.raise_for_status()

    result = response.json()
    new_thread_id = result.get("id", 0)
    comments = result.get("comments", [{}])
    comment_id = comments[0].get("id", 0) if comments else 0

    if resolve_after_posting and new_thread_id:
        resolve_thread_by_id(
            requests,
            headers,
            config,
            repo_id,
            pull_request_id,
            new_thread_id,
            status="closed",
        )

    return AddCommentResult(
        thread_id=new_thread_id,
        comment_id=comment_id,
    )


def update_review_narrative(
    config: AzureDevOpsConfig,
    pat: str,
    pull_request_id: int,
    content: str,
    review_state: Any = None,
) -> UpdateNarrativeResult:
    """Update the Review Narrative in the overall PR summary comment.

    When *review_state* is provided, it is used directly. Otherwise, the
    review state is loaded from disk (matching the current CLI behaviour).

    Args:
        config: An :class:`~agentic_devtools.cli.azure_devops.config.AzureDevOpsConfig`.
        pat: Azure DevOps Personal Access Token.
        pull_request_id: The PR ID.
        content: New narrative content.
        review_state: Optional pre-loaded review state object. When *None*,
            the state is loaded from disk.

    Returns:
        An :class:`UpdateNarrativeResult`.

    Raises:
        FileNotFoundError: When the review state file does not exist and
            *review_state* is not provided.
    """
    from agentic_devtools.cli.azure_devops.auth import get_auth_headers
    from agentic_devtools.cli.azure_devops.helpers import (
        get_repository_id,
        patch_comment,
        require_requests,
    )
    from agentic_devtools.cli.azure_devops.review_scaffold import build_pr_base_url
    from agentic_devtools.cli.azure_devops.review_state import load_review_state, save_review_state
    from agentic_devtools.cli.azure_devops.review_templates import render_overall_summary

    requests = require_requests()
    headers = get_auth_headers(pat)

    if review_state is None:
        review_state = load_review_state(pull_request_id)

    repo_id = getattr(review_state, "repoId", None)
    if not repo_id:
        repo_id = get_repository_id(config.organization, config.project, config.repository)

    review_state.overallSummary.narrativeSummary = content
    base_url = build_pr_base_url(config, pull_request_id)
    new_content = render_overall_summary(review_state, base_url)

    thread_id = review_state.overallSummary.threadId
    comment_id = review_state.overallSummary.commentId
    patch_comment(requests, headers, config, repo_id, pull_request_id, thread_id, comment_id, new_content)
    save_review_state(review_state)

    return UpdateNarrativeResult(
        success=True,
        message="Review Narrative updated successfully.",
    )


# ---------------------------------------------------------------------------
# Stub functions (planned for future implementation)
# ---------------------------------------------------------------------------


def add_reviewer(
    config: AzureDevOpsConfig,
    pat: str,
    pull_request_id: int,
    reviewer_id: str,
) -> AddReviewerResult:
    """Add a reviewer to a pull request.

    .. note::
        Not yet implemented. Raises :exc:`NotImplementedError`.

    Args:
        config: An :class:`~agentic_devtools.cli.azure_devops.config.AzureDevOpsConfig`.
        pat: Azure DevOps Personal Access Token.
        pull_request_id: The PR ID.
        reviewer_id: The reviewer's identity.

    Raises:
        NotImplementedError: Always.
    """
    raise NotImplementedError("Planned for future implementation")


def complete_pull_request(
    config: AzureDevOpsConfig,
    pat: str,
    pull_request_id: int,
    merge_strategy: str = "squash",
) -> CompletePullRequestResult:
    """Complete (merge) a pull request.

    .. note::
        Not yet implemented. Raises :exc:`NotImplementedError`.

    Args:
        config: An :class:`~agentic_devtools.cli.azure_devops.config.AzureDevOpsConfig`.
        pat: Azure DevOps Personal Access Token.
        pull_request_id: The PR ID.
        merge_strategy: Merge strategy (default ``"squash"``).

    Raises:
        NotImplementedError: Always.
    """
    raise NotImplementedError("Planned for future implementation")


def file_review(
    config: AzureDevOpsConfig,
    pat: str,
    pull_request_id: int,
    file_path: str,
    status: str = "approved",
    comment: str | None = None,
) -> FileReviewResult:
    """Submit a review for a specific file in a pull request.

    .. note::
        Not yet implemented. Raises :exc:`NotImplementedError`.

    Args:
        config: An :class:`~agentic_devtools.cli.azure_devops.config.AzureDevOpsConfig`.
        pat: Azure DevOps Personal Access Token.
        pull_request_id: The PR ID.
        file_path: Path of the file being reviewed.
        status: Review status (e.g. ``"approved"``, ``"needs-work"``).
        comment: Optional review comment.

    Raises:
        NotImplementedError: Always.
    """
    raise NotImplementedError("Planned for future implementation")
