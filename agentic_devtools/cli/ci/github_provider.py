"""GitHub Actions CI platform provider.

Implements the ``CIPlatformProvider`` interface for GitHub Actions,
using the ``gh`` CLI for API calls consistent with existing codebase patterns.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from agentic_devtools.cli.ci.exceptions import MalformedEventError
from agentic_devtools.cli.ci.models import (
    CheckRunStatus,
    EventPayload,
    PRMetadata,
    ReviewInfo,
)
from agentic_devtools.cli.ci.provider import CIPlatformProvider
from agentic_devtools.cli.ci.retry import RetryableError, retry_with_backoff
from agentic_devtools.cli.subprocess_utils import run_safe

logger = logging.getLogger(__name__)


def _gh_api(endpoint: str, *, method: str = "GET", body: dict | None = None, paginate: bool = False) -> str:
    """Call the GitHub API via the ``gh`` CLI.

    Args:
        endpoint: API endpoint path (e.g., "/repos/{owner}/{repo}/pulls/1").
        method: HTTP method.
        body: JSON body for POST/PATCH/PUT requests.
        paginate: Whether to use --paginate for list endpoints.

    Returns:
        Raw response body as string.

    Raises:
        RetryableError: On rate limit (HTTP 403/429) or transient failure.
        RuntimeError: On non-retryable API errors.
    """
    cmd = ["gh", "api", endpoint, "--method", method]
    if paginate:
        cmd.append("--paginate")
    if body is not None:
        cmd.extend(["--input", "-"])

    result = run_safe(
        cmd,
        capture_output=True,
        text=True,
        shell=False,
        input=json.dumps(body) if body else None,
    )

    if result.returncode != 0:
        stderr = result.stderr.strip()
        stderr_lower = stderr.lower()
        # GitHub rate limit responses — only match actual rate-limit indicators,
        # not generic 403 (which covers permissions, SSO, access restrictions).
        if (
            "rate limit" in stderr_lower
            or "secondary rate limit" in stderr_lower
            or "429" in stderr
        ):
            raise RetryableError(f"GitHub API rate limited: {stderr}")
        # Server errors are retryable
        if any(code in stderr for code in ("500", "502", "503", "504")):
            raise RetryableError(f"GitHub API server error: {stderr}")
        raise RuntimeError(f"GitHub API error: {stderr}")

    return result.stdout


def _parse_paginated_json(raw: str) -> Any:
    """Parse potentially concatenated JSON from ``gh api --paginate``.

    ``gh api --paginate`` may emit multiple JSON documents (one per page)
    for non-array endpoints. This handles both single documents and
    concatenated documents by attempting incremental parsing.

    Returns:
        Merged result — arrays are concatenated; objects with array
        values have those arrays merged across pages.
    """
    raw = raw.strip()
    if not raw:
        return []

    # Try single document first (most common case / single page)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Parse concatenated JSON documents
    decoder = json.JSONDecoder()
    results: list[Any] = []
    idx = 0
    while idx < len(raw):
        while idx < len(raw) and raw[idx] in " \t\n\r":
            idx += 1
        if idx >= len(raw):  # pragma: no cover — strip() above removes trailing ws
            break
        try:
            obj, end_idx = decoder.raw_decode(raw, idx)
        except json.JSONDecodeError as exc:
            snippet = raw[idx:idx + 80]
            raise json.JSONDecodeError(
                f"Failed to parse concatenated JSON at index {idx} "
                f"(snippet: {snippet!r}): {exc.msg}",
                raw,
                idx,
            ) from exc
        results.append(obj)
        idx = end_idx

    if not results:  # pragma: no cover — non-empty stripped input always yields results or raises
        return []

    # If all pages are arrays, concatenate them
    if isinstance(results[0], list):
        merged: list[Any] = []
        for r in results:
            if isinstance(r, list):
                merged.extend(r)
        return merged

    # For objects (e.g., check_runs wrapped response), merge array values.
    # Note: For non-list keys, only the first page's value is preserved.
    # If a later page has a different scalar value for the same key, a warning
    # is logged since this indicates an unexpected response shape.
    if isinstance(results[0], dict):
        merged_dict: dict[str, Any] = {}
        for r in results:
            if not isinstance(r, dict):
                continue
            for key, value in r.items():
                if key not in merged_dict:
                    merged_dict[key] = value
                elif isinstance(value, list) and isinstance(merged_dict[key], list):
                    merged_dict[key].extend(value)
                elif not isinstance(value, list) and merged_dict[key] != value:
                    logger.warning(
                        "_parse_paginated_json: scalar key %r differs across pages "
                        "(first=%r, later=%r); keeping first page value",
                        key,
                        merged_dict[key],
                        value,
                    )
        return merged_dict

    return results


class GitHubActionsProvider(CIPlatformProvider):
    """GitHub Actions implementation of the CI platform provider.

    Uses the ``gh`` CLI for all API interactions, with retry logic
    for transient failures and rate limiting.
    """

    def __init__(self, repo: str = "") -> None:
        """Initialize the GitHub Actions provider.

        Args:
            repo: Repository in "owner/repo" format. If empty, uses the
                current repository context from ``gh``.
        """
        self._repo = repo

    def _repo_api(self, path: str) -> str:
        """Build a repository-scoped API path."""
        if self._repo:
            return f"/repos/{self._repo}{path}"
        return path

    def parse_event(self, raw_payload: dict, event_name: str) -> EventPayload:
        """Parse a GitHub Actions event payload."""
        try:
            if event_name in ("pull_request", "pull_request_target"):
                return self._parse_pull_request_event(raw_payload)
            if event_name == "pull_request_review":
                return self._parse_pull_request_review_event(raw_payload, event_name)
            if event_name == "issues":
                return self._parse_issues_event(raw_payload)
            if event_name == "workflow_run":
                return self._parse_workflow_run_event(raw_payload, event_name)
        except (KeyError, TypeError) as exc:
            raise MalformedEventError(event_name, str(exc)) from exc

        raise MalformedEventError(event_name, f"unsupported event type: {event_name}")

    def _parse_pull_request_event(self, raw: dict) -> EventPayload:
        pr = raw["pull_request"]
        return EventPayload(
            pr_number=pr["number"],
            head_branch=pr["head"]["ref"],
            head_sha=pr["head"]["sha"],
            base_branch=pr["base"]["ref"],
            action=raw.get("action", ""),
            repository_full_name=raw.get("repository", {}).get("full_name", ""),
        )

    def _parse_pull_request_review_event(self, raw: dict, event_name: str) -> EventPayload:
        pr = raw.get("pull_request")
        if pr is None:
            raise MalformedEventError(event_name, "missing 'pull_request' field")
        return EventPayload(
            pr_number=pr["number"],
            head_branch=pr["head"]["ref"],
            head_sha=pr["head"]["sha"],
            base_branch=pr["base"]["ref"],
            action=raw.get("action", ""),
            repository_full_name=raw.get("repository", {}).get("full_name", ""),
        )

    def _parse_issues_event(self, raw: dict) -> EventPayload:
        label = raw.get("label", {})
        return EventPayload(
            action=raw.get("action", ""),
            trigger_label=label.get("name", ""),
            repository_full_name=raw.get("repository", {}).get("full_name", ""),
        )

    def _parse_workflow_run_event(self, raw: dict, event_name: str) -> EventPayload:
        wf = raw.get("workflow_run")
        if wf is None:
            raise MalformedEventError(event_name, "missing 'workflow_run' field")

        # Try to extract PR info from the workflow run
        pr_number = 0
        base_branch = ""
        prs = wf.get("pull_requests", [])
        if prs:
            pr_number = prs[0].get("number", 0)
            base_branch = prs[0].get("base", {}).get("ref", "")

        return EventPayload(
            pr_number=pr_number,
            head_branch=wf.get("head_branch", ""),
            head_sha=wf.get("head_sha", ""),
            base_branch=base_branch,
            action=raw.get("action", ""),
            repository_full_name=raw.get("repository", {}).get("full_name", ""),
        )

    @retry_with_backoff()
    def get_pr_metadata(self, pr_number: int) -> PRMetadata:
        """Retrieve PR metadata via gh CLI."""
        response = _gh_api(self._repo_api(f"/pulls/{pr_number}"))
        data = json.loads(response)
        return PRMetadata(
            number=data["number"],
            title=data["title"],
            head_branch=data["head"]["ref"],
            head_sha=data["head"]["sha"],
            base_branch=data["base"]["ref"],
            head_repo_full_name=data.get("head", {}).get("repo", {}).get("full_name", ""),
            base_repo_full_name=data.get("base", {}).get("repo", {}).get("full_name", ""),
            labels=[lbl["name"] for lbl in data.get("labels", [])],
            is_draft=data.get("draft", False),
            mergeable=data.get("mergeable"),
        )

    @retry_with_backoff()
    def list_check_runs(self, head_sha: str) -> list[CheckRunStatus]:
        """List check runs for a commit SHA."""
        response = _gh_api(self._repo_api(f"/commits/{head_sha}/check-runs"), paginate=True)
        data = _parse_paginated_json(response)
        return [
            CheckRunStatus(
                id=cr["id"],
                name=cr["name"],
                status=cr["status"],
                conclusion=cr.get("conclusion") or "",
            )
            for cr in data.get("check_runs", [])
        ]

    @retry_with_backoff()
    def list_reviews(self, pr_number: int) -> list[ReviewInfo]:
        """List reviews for a pull request."""
        response = _gh_api(self._repo_api(f"/pulls/{pr_number}/reviews"), paginate=True)
        reviews = _parse_paginated_json(response)
        return [
            ReviewInfo(
                id=r["id"],
                user=r["user"]["login"],
                state=r["state"],
                body=r.get("body") or "",
            )
            for r in reviews
        ]

    @retry_with_backoff()
    def post_comment(self, pr_number: int, body: str) -> int:
        """Post a comment on a PR issue."""
        response = _gh_api(
            self._repo_api(f"/issues/{pr_number}/comments"),
            method="POST",
            body={"body": body},
        )
        data = json.loads(response)
        return data["id"]

    @retry_with_backoff()
    def update_comment(self, comment_id: int, body: str) -> None:
        """Update an existing comment."""
        _gh_api(
            self._repo_api(f"/issues/comments/{comment_id}"),
            method="PATCH",
            body={"body": body},
        )

    @retry_with_backoff()
    def find_comment(self, pr_number: int, marker: str) -> tuple[int, str] | None:
        """Find a comment containing a marker string."""
        response = _gh_api(self._repo_api(f"/issues/{pr_number}/comments"), paginate=True)
        comments = _parse_paginated_json(response)
        for comment in comments:
            if marker in comment.get("body", ""):
                return (comment["id"], comment["body"])
        return None

    @retry_with_backoff()
    def approve_pr(self, pr_number: int, head_sha: str, body: str) -> None:
        """Approve a pull request."""
        _gh_api(
            self._repo_api(f"/pulls/{pr_number}/reviews"),
            method="POST",
            body={"commit_id": head_sha, "event": "APPROVE", "body": body},
        )

    @retry_with_backoff()
    def merge_pr(self, pr_number: int, head_sha: str, method: str) -> None:
        """Merge a pull request."""
        _gh_api(
            self._repo_api(f"/pulls/{pr_number}/merge"),
            method="PUT",
            body={"sha": head_sha, "merge_method": method},
        )

    @retry_with_backoff()
    def request_reviewer(self, pr_number: int, reviewer: str) -> None:
        """Request a reviewer for a pull request."""
        _gh_api(
            self._repo_api(f"/pulls/{pr_number}/requested_reviewers"),
            method="POST",
            body={"reviewers": [reviewer]},
        )

    @retry_with_backoff()
    def list_pr_files(self, pr_number: int) -> list[str]:
        """List files changed in a pull request."""
        response = _gh_api(self._repo_api(f"/pulls/{pr_number}/files"), paginate=True)
        files = _parse_paginated_json(response)
        return [f["filename"] for f in files]

    @retry_with_backoff()
    def get_check_annotations(self, check_run_id: int, limit: int) -> list[str]:
        """Get annotations from a check run."""
        response = _gh_api(self._repo_api(f"/check-runs/{check_run_id}/annotations"))
        annotations = json.loads(response)
        return [a.get("message", "") for a in annotations[:limit]]
