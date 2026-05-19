"""GitHub Actions CI platform provider.

Implements the ``CIPlatformProvider`` interface for GitHub Actions,
using the ``gh`` CLI for API calls consistent with existing codebase patterns.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from agentic_devtools.cli.ci.exceptions import MalformedEventError
from agentic_devtools.cli.ci.models import (
    CheckRunStatus,
    EventPayload,
    PRMetadata,
    ReviewCommentInfo,
    ReviewInfo,
)
from agentic_devtools.cli.ci.provider import CIPlatformProvider
from agentic_devtools.cli.ci.retry import RetryableError, retry_with_backoff
from agentic_devtools.cli.github.request_copilot_review import request_copilot_review as _request_copilot_review
from agentic_devtools.cli.github.resolve_review_threads import resolve_review_threads as _resolve_review_threads
from agentic_devtools.cli.subprocess_utils import run_safe

logger = logging.getLogger(__name__)

_ADDRESSED_REPLY_BODY = "Addressed on the updated PR branch."
_LEGACY_ADDRESSED_REPLY_PREFIXES = ("addressed by fix commit",)


def _format_suppressed_body(body: str, max_length: int = 200) -> str:
    """Normalize/escape/truncate suppressed body for compact one-line trigger output."""
    normalized = " ".join(body.split())
    escaped = normalized.replace('"', '\\"')
    if len(escaped) <= max_length:
        return escaped
    return escaped[: max_length - 1].rstrip() + "…"


def _comment_is_suppressed(comment: dict[str, Any]) -> bool:
    """Return True when API payload indicates the review comment is minimized/suppressed."""
    return bool(
        comment.get("is_suppressed")
        or comment.get("is_minimized")
        or comment.get("minimized")
        or bool(comment.get("minimized_reason"))
    )


def _build_repair_comment(
    *,
    head_sha: str,
    repair_type: str,
    failed_checks: list[CheckRunStatus],
    review_comments: list[ReviewCommentInfo],
    repository_full_name: str = "",
    pr_number: int = 0,
    review_id: int = 0,
) -> str:
    """Build the @copilot-tagged comment body for repair dispatch.

    The comment MUST begin with ``@copilot`` for reliable AI agent session
    triggering. This is a hard requirement — comments that tag @copilot
    but don't begin with @copilot have been observed to trigger agent
    sessions unreliably.

    Args:
        head_sha: Current HEAD SHA for context.
        repair_type: ``"review"``, ``"ci"``, or ``"both"``.
        failed_checks: List of failed check runs (for CI repair context).
        review_comments: Rich review comment metadata (for review repair context).
        repository_full_name: Full repository name (e.g., ``"owner/repo"``).
        pr_number: Pull request number (for building review and comment URLs).
        review_id: ID of the Copilot review that triggered this dispatch.
            Used for the dedup marker and review URL.

    Returns:
        Comment body string beginning with ``@copilot``.
    """
    parts: list[str] = ["@copilot"]

    has_review = repair_type in ("review", "both")
    has_review_comments = has_review and bool(review_comments)
    has_ci = repair_type in ("ci", "both") and bool(failed_checks)

    if has_review and review_id:
        # Dedup marker so the agent can identify which review triggered this
        parts.append(f"<!-- copilot-trigger:{review_id} -->")

        if repository_full_name and "/" in repository_full_name and pr_number and review_id:
            review_url = f"https://github.com/{repository_full_name}/pull/{pr_number}#pullrequestreview-{review_id}"
            parts.append("")
            parts.append(f"[Review]({review_url})")

    if has_review_comments:
        parts.append("")
        parts.append("## Comments")
        parts.append("")

        basename_paths: dict[str, set[str]] = {}
        for comment in review_comments:
            basename = comment.path.rsplit("/", 1)[-1] if "/" in comment.path else comment.path
            basename_paths.setdefault(basename, set()).add(comment.path)

        file_counters: dict[str, int] = {}
        for nc, comment in enumerate(review_comments, 1):
            basename = comment.path.rsplit("/", 1)[-1] if "/" in comment.path else comment.path
            filename = comment.path if len(basename_paths.get(basename, set())) > 1 else basename
            file_counters[comment.path] = file_counters.get(comment.path, 0) + 1
            nf = file_counters[comment.path]

            if comment.is_suppressed:
                body = _format_suppressed_body(comment.body)
                parts.append(f'- Comment #{nc} - {filename} ({nf}): "{body}" (suppressed comment)')
            else:
                label = f"Comment #{nc} - {filename} ({nf})"
                if comment.html_url:
                    parts.append(f"- [{label}]({comment.html_url})")
                else:
                    parts.append(f"- {label}")

    if has_ci:
        parts.append("")
        parts.append("## CI Failures")
        parts.append("")
        for check in failed_checks:
            # Only use html_url from the API response — the check run ID does not
            # match the Actions workflow run ID, so omit the link entirely when
            # html_url is absent to avoid emitting a broken /runs/{id} URL.
            job_url = check.html_url
            if job_url:
                parts.append(f"- ❌ [{check.name}]({job_url}) — `{check.conclusion}`")
            else:
                parts.append(f"- ❌ {check.name} — `{check.conclusion}`")

    has_review_context = has_review and bool(review_id)
    if not review_comments and not failed_checks and not has_review_context:
        parts.append("")
        parts.append(f"Please review the PR and fix any issues found. Current HEAD: `{head_sha[:8]}`.")
        parts.append("")
        parts.append("---")
        parts.append(f"*Automated repair dispatch for commit `{head_sha[:8]}` (type: {repair_type})*")
        return "\n".join(parts)

    # Choose the appropriate skill based on what triggered the repair
    if repair_type == "ci":
        skill = "agdt.address-copilot-review.ci-repair.agent.md"
    else:
        skill = "agdt.address-copilot-review.evaluate-and-respond.agent.md"

    parts.append("")
    parts.append("## Instructions")
    parts.append("")
    parts.append(f"Follow `.github/agents/{skill}`")

    return "\n".join(parts)


def _gh_api(
    endpoint: str,
    *,
    method: str = "GET",
    body: dict | None = None,
    paginate: bool = False,
    token: str | None = None,
) -> str:
    """Call the GitHub API via the ``gh`` CLI.

    Args:
        endpoint: API endpoint path (e.g., "/repos/{owner}/{repo}/pulls/1").
        method: HTTP method.
        body: JSON body for POST/PATCH/PUT requests.
        paginate: Whether to use --paginate for list endpoints.
        token: Optional token to use instead of the default ``GH_TOKEN``.
            When provided, the subprocess environment is overridden so that
            ``gh`` authenticates with this token.

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

    env: dict[str, str] | None = None
    if token:
        env = {**os.environ, "GH_TOKEN": token}

    result = run_safe(
        cmd,
        capture_output=True,
        text=True,
        shell=False,
        input=json.dumps(body) if body else None,
        env=env,
    )

    if result.returncode != 0:
        stderr = result.stderr.strip()
        stderr_lower = stderr.lower()
        # GitHub rate limit responses — only match actual rate-limit indicators,
        # not generic 403 (which covers permissions, SSO, access restrictions).
        if "rate limit" in stderr_lower or "secondary rate limit" in stderr_lower or "429" in stderr:
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
            snippet = raw[idx : idx + 80]
            raise json.JSONDecodeError(
                f"Failed to parse concatenated JSON at index {idx} (snippet: {snippet!r}): {exc.msg}",
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
            if event_name == "issue_comment":
                return self._parse_issue_comment_event(raw_payload, event_name)
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
            sender_login=raw.get("sender", {}).get("login", ""),
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
            sender_login=raw.get("sender", {}).get("login", ""),
        )

    def _parse_issues_event(self, raw: dict) -> EventPayload:
        label = raw.get("label", {})
        return EventPayload(
            action=raw.get("action", ""),
            trigger_label=label.get("name", ""),
            repository_full_name=raw.get("repository", {}).get("full_name", ""),
            sender_login=raw.get("sender", {}).get("login", ""),
        )

    def _parse_issue_comment_event(self, raw: dict, event_name: str) -> EventPayload:
        issue = raw.get("issue")
        if issue is None:
            raise MalformedEventError(event_name, "missing 'issue' field")
        if issue.get("pull_request") is None:
            raise MalformedEventError(event_name, "issue_comment is not on a pull request")
        issue_number = issue.get("number")
        if not isinstance(issue_number, int) or issue_number <= 0:
            raise MalformedEventError(event_name, "missing or invalid 'issue.number' field")
        commenter_login = raw.get("comment", {}).get("user", {}).get("login", "")
        return EventPayload(
            pr_number=issue_number,
            action="comment_created",
            repository_full_name=raw.get("repository", {}).get("full_name", ""),
            sender_login=commenter_login or raw.get("sender", {}).get("login", ""),
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
            sender_login=raw.get("sender", {}).get("login", ""),
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
            requested_reviewers=[reviewer["login"] for reviewer in data.get("requested_reviewers", [])],
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
                html_url=cr.get("html_url") or "",
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
                commit_sha=r.get("commit_id") or "",
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
        """Approve a pull request.

        Uses ``AGDT_PR_APPROVER_PAT`` when set so that the approval comes from
        a separate identity (GitHub prevents approving your own PR).  When the
        variable is unset or empty the approval is skipped with a warning.
        """
        approver_token = os.environ.get("AGDT_PR_APPROVER_PAT", "").strip()
        if not approver_token:
            logger.warning(
                "AGDT_PR_APPROVER_PAT is not configured. "
                "Cannot approve PR without a dedicated approver token. "
                "See repository documentation for setup instructions."
            )
            return

        try:
            _gh_api(
                self._repo_api(f"/pulls/{pr_number}/reviews"),
                method="POST",
                body={"commit_id": head_sha, "event": "APPROVE", "body": body},
                token=approver_token,
            )
        except RuntimeError as exc:
            stderr = str(exc)
            if "401" in stderr or "Bad credentials" in stderr.lower():
                logger.warning(
                    "AGDT_PR_APPROVER_PAT authentication failed (401). "
                    "The token may be expired or invalid. "
                    "Skipping PR approval. Rotate the secret and retry."
                )
                return
            raise

    @retry_with_backoff()
    def merge_pr(self, pr_number: int, head_sha: str, method: str) -> None:
        """Merge a pull request."""
        _gh_api(
            self._repo_api(f"/pulls/{pr_number}/merge"),
            method="PUT",
            body={"sha": head_sha, "merge_method": method},
        )

    @retry_with_backoff()
    def publish_pr(self, pr_number: int) -> None:
        """Mark a draft PR as ready for review via gh pr ready command."""
        cmd = ["gh", "pr", "ready", str(pr_number)]
        if self._repo:
            cmd.extend(["--repo", self._repo])
        result = run_safe(cmd, capture_output=True, text=True, shell=False)
        if result.returncode != 0:
            error_message = result.stderr.strip() or result.stdout.strip() or "Unknown error"
            raise RuntimeError(f"Failed to publish PR #{pr_number}: {error_message}")

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

    @retry_with_backoff()
    def dispatch_repair(
        self,
        pr_number: int,
        head_sha: str,
        repair_type: str,
        failed_checks: list[CheckRunStatus],
        review_comments: list[ReviewCommentInfo],
        review_id: int = 0,
    ) -> int:
        """Post a @copilot-tagged comment to trigger an AI agent repair session.

        The comment MUST begin with ``@copilot`` for reliable agent triggering.
        Uses ``AGDT_PR_APPROVER_PAT`` for authentication to ensure
        ``issues:write`` access.  ``COPILOT_GITHUB_TOKEN`` is fine-grained and
        lacks this permission, causing 403 errors when posting comments.
        """
        body = _build_repair_comment(
            head_sha=head_sha,
            repair_type=repair_type,
            failed_checks=failed_checks,
            review_comments=review_comments,
            repository_full_name=(self._repo or os.environ.get("GITHUB_REPOSITORY", "")),
            pr_number=pr_number,
            review_id=review_id,
        )

        # Use AGDT_PR_APPROVER_PAT for posting comments (has issues:write permission).
        # COPILOT_GITHUB_TOKEN is fine-grained and lacks issues:write access.
        token = os.environ.get("AGDT_PR_APPROVER_PAT", "").strip() or None

        response = _gh_api(
            self._repo_api(f"/issues/{pr_number}/comments"),
            method="POST",
            body={"body": body},
            token=token,
        )
        data = json.loads(response)
        return data["id"]

    @retry_with_backoff()
    def list_review_comments(self, pr_number: int, review_id: int) -> list[ReviewCommentInfo]:
        """List inline comments from a specific review."""
        response = _gh_api(
            self._repo_api(f"/pulls/{pr_number}/reviews/{review_id}/comments"),
            paginate=True,
        )
        comments = _parse_paginated_json(response)
        return [
            ReviewCommentInfo(
                id=int(c["id"]),
                path=c.get("path", ""),
                body=c.get("body", ""),
                html_url=c.get("html_url", ""),
                is_suppressed=_comment_is_suppressed(c),
            )
            for c in comments
        ]

    def _run_git(self, args: Iterable[str]) -> str:
        """Run git command and return stdout or raise on failure."""
        result = run_safe(
            ["git", *args],
            capture_output=True,
            text=True,
            shell=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
        return result.stdout

    @retry_with_backoff()
    def _list_review_comment_ids(self, pr_number: int, review_id: int) -> list[int]:
        """Return numeric review comment IDs for a given review."""
        response = _gh_api(
            self._repo_api(f"/pulls/{pr_number}/reviews/{review_id}/comments"),
            paginate=True,
        )
        comments = _parse_paginated_json(response)
        return [int(c["id"]) for c in comments if c.get("id")]

    @retry_with_backoff()
    def _reply_to_review_comment(self, pr_number: int, comment_id: int) -> None:
        """Post addressed reply to a single review comment."""
        _gh_api(
            self._repo_api(f"/pulls/{pr_number}/comments/{comment_id}/replies"),
            method="POST",
            body={"body": _ADDRESSED_REPLY_BODY},
        )

    @retry_with_backoff()
    def _list_addressed_reply_parent_comment_ids(self, pr_number: int) -> set[int]:
        """Return parent comment IDs that already have an addressed reply."""
        response = _gh_api(
            self._repo_api(f"/pulls/{pr_number}/comments"),
            paginate=True,
        )
        comments = _parse_paginated_json(response)
        return {
            int(comment["in_reply_to_id"])
            for comment in comments
            if comment.get("in_reply_to_id")
            and (
                str(comment.get("body", "")).strip().lower() == _ADDRESSED_REPLY_BODY.lower()
                or str(comment.get("body", "")).strip().lower().startswith(_LEGACY_ADDRESSED_REPLY_PREFIXES)
            )
        }

    def _has_existing_addressed_reply(
        self,
        pr_number: int,
        comment_id: int,
        addressed_reply_parent_comment_ids: set[int] | None = None,
    ) -> bool:
        """Check whether a review comment already has an addressed reply."""
        parent_comment_ids = (
            addressed_reply_parent_comment_ids
            if addressed_reply_parent_comment_ids is not None
            else self._list_addressed_reply_parent_comment_ids(pr_number)
        )
        return comment_id in parent_comment_ids

    def _build_squash_commit_message(self, head_sha: str, commit_subjects: list[str]) -> str:
        """Build a deterministic squash commit message."""
        unique_subjects = [subject.strip() for subject in commit_subjects if subject.strip()]
        if not unique_subjects:
            return f"chore: post-repair squash for {head_sha[:8]}"
        if len(unique_subjects) == 1:
            return unique_subjects[0]
        bullets = "\n".join(f"- {subject}" for subject in unique_subjects[:10])
        return f"chore: squash post-repair updates\n\n{bullets}\n\nAutomated squash for `{head_sha[:8]}`."

    @staticmethod
    def _clean_sdk_commit_message(raw: str) -> str | None:
        """Strip fences and conversational prefixes, then validate Conventional Commit format.

        Returns the cleaned commit message if it passes basic format validation,
        or ``None`` if the SDK output should be discarded and the deterministic
        fallback used instead.
        """
        message = raw.strip()
        if not message:
            return None

        # Strip markdown fences.
        if message.startswith("```"):
            lines = message.splitlines()
            if len(lines) >= 3 and lines[0].startswith("```") and lines[-1].strip() == "```":
                message = "\n".join(lines[1:-1]).strip()

        # Strip "commit message:" conversational prefix.
        if message.lower().startswith("commit message:"):
            message = message.split(":", 1)[1].strip()

        if not message:
            return None

        subject = message.splitlines()[0].strip()

        # Reject conversational openers that indicate the model narrated its output
        # instead of returning the commit message directly.
        _CONVERSATIONAL_STARTERS = (
            "here ",
            "here's ",
            "i'll ",
            "i've ",
            "i ",
            "sure,",
            "below is",
            "certainly ",
            "the following",
            "this commit",
        )
        if subject.lower().startswith(_CONVERSATIONAL_STARTERS):
            logger.warning(
                "Rejecting SDK commit message with conversational opener: %r",
                subject[:60],
            )
            return None

        # Cap subject line to 100 characters.
        if len(subject) > 100:
            logger.warning(
                "Rejecting SDK commit message with subject too long (%d chars)",
                len(subject),
            )
            return None

        # Require Conventional Commit format: type[(scope)][!]: description.
        if not re.match(r"^[a-z][\w-]*(?:\([^)]*\))?!?:\s+\S", subject):
            logger.warning(
                "Rejecting SDK commit message that doesn't follow Conventional Commits: %r",
                subject[:60],
            )
            return None

        return message

    def _generate_commit_message_via_sdk(
        self,
        *,
        head_sha: str,
        commit_subjects: list[str],
        timeout_seconds: int = 60,
    ) -> str | None:
        """Attempt to generate a squash commit message via Copilot SDK."""
        token = os.environ.get("COPILOT_GITHUB_TOKEN", "").strip()
        if not token:
            return None

        try:
            from copilot import CopilotClient, SubprocessConfig
            from copilot.session import PermissionHandler
        except Exception as exc:  # pragma: no cover - optional dependency/runtime
            logger.warning("Copilot SDK unavailable for squash commit message generation: %s", exc)
            return None

        model = os.environ.get("COPILOT_MODEL", "claude-opus-4.6")
        unique_subjects = [subject.strip() for subject in commit_subjects if subject.strip()]
        subjects_text = "\n".join(f"- {subject}" for subject in unique_subjects[:20]) or "- (none)"
        prompt = (
            "Generate a concise Conventional Commit message for squashing this pull request.\n"
            "Return plain commit message text only (subject + optional body), no markdown fences.\n\n"
            f"Head SHA: {head_sha}\n"
            "Commit subjects:\n"
            f"{subjects_text}\n"
        )

        async def _run() -> str | None:
            client = None
            session = None
            content_parts: list[str] = []
            error_messages: list[str] = []
            done = asyncio.Event()
            try:
                client = CopilotClient(SubprocessConfig(github_token=token))
                await client.start()
                try:
                    session = await client.create_session(
                        model=model,
                        on_permission_request=PermissionHandler.approve_all,
                        infinite_sessions={"enabled": False},
                        github_token=token,
                    )
                except TypeError as exc:
                    if "unexpected keyword argument" not in str(exc) or "github_token" not in str(exc):
                        raise  # pragma: no cover - defensive re-raise for unrelated TypeErrors
                    session = await client.create_session(
                        model=model,
                        on_permission_request=PermissionHandler.approve_all,
                        infinite_sessions={"enabled": False},
                    )

                def on_event(event: Any) -> None:
                    event_type = getattr(getattr(event, "type", None), "value", "")
                    if event_type == "assistant.message":
                        content_parts.append(getattr(getattr(event, "data", None), "content", ""))
                    elif event_type == "session.idle":
                        done.set()
                    elif event_type in {"error", "session.error", "assistant.error"}:
                        msg = getattr(getattr(event, "data", None), "message", None) or str(getattr(event, "data", ""))
                        error_messages.append(f"{event_type}: {msg}")
                        done.set()

                session.on(on_event)
                await session.send(prompt)
                await done.wait()

                if error_messages:
                    logger.warning("Copilot SDK returned errors for squash message: %s", "; ".join(error_messages))
                    return None

                raw = (content_parts[-1] if content_parts else "").strip()
                if not raw:
                    return None
                return GitHubActionsProvider._clean_sdk_commit_message(raw)
            except Exception as exc:  # pragma: no cover - defensive runtime fallback
                logger.warning("Copilot SDK commit message generation failed: %s", exc)
                return None
            finally:
                if session is not None:
                    try:
                        await session.disconnect()
                    except Exception:  # pragma: no cover - defensive cleanup
                        pass
                if client is not None:
                    try:
                        await client.stop()
                    except Exception:  # pragma: no cover - defensive cleanup
                        pass

        try:
            return asyncio.run(asyncio.wait_for(_run(), timeout=timeout_seconds))
        except asyncio.TimeoutError:
            logger.warning("Copilot SDK commit message generation timed out after %ss", timeout_seconds)
            return None
        except RuntimeError as exc:  # pragma: no cover - defensive runtime fallback
            logger.warning("Copilot SDK commit message generation could not start event loop: %s", exc)
            return None

    def _resolve_conflicted_file_content_via_sdk(
        self,
        *,
        file_path: str,
        conflict_content: str,
        base_branch: str,
        head_branch: str,
        timeout_seconds: int = 90,
    ) -> str | None:
        """Attempt to resolve a single conflicted file via Copilot SDK."""
        token = os.environ.get("COPILOT_GITHUB_TOKEN", "").strip()
        if not token:
            return None

        try:
            from copilot import CopilotClient, SubprocessConfig
            from copilot.session import PermissionHandler
        except Exception as exc:  # pragma: no cover - optional dependency/runtime
            logger.warning("Copilot SDK unavailable for conflict resolution: %s", exc)
            return None

        model = os.environ.get("COPILOT_MODEL", "claude-opus-4.6")
        prompt = (
            "You are resolving a git rebase conflict.\n"
            "Preserve valid changes from both sides where possible.\n"
            "Output ONLY the final resolved file content with all conflict markers removed.\n"
            "Do not wrap output in markdown fences.\n\n"
            f"Base branch: {base_branch}\n"
            f"Head branch: {head_branch}\n"
            f"File path: {file_path}\n\n"
            "Conflicted file content:\n"
            f"{conflict_content}\n"
        )

        async def _run() -> str | None:
            client = None
            session = None
            content_parts: list[str] = []
            error_messages: list[str] = []
            done = asyncio.Event()
            try:
                client = CopilotClient(SubprocessConfig(github_token=token))
                await client.start()
                try:
                    session = await client.create_session(
                        model=model,
                        on_permission_request=PermissionHandler.approve_all,
                        infinite_sessions={"enabled": False},
                        github_token=token,
                    )
                except TypeError as exc:
                    if "unexpected keyword argument" not in str(exc) or "github_token" not in str(exc):
                        raise  # pragma: no cover - defensive re-raise for unrelated TypeErrors
                    session = await client.create_session(
                        model=model,
                        on_permission_request=PermissionHandler.approve_all,
                        infinite_sessions={"enabled": False},
                    )

                def on_event(event: Any) -> None:
                    event_type = getattr(getattr(event, "type", None), "value", "")
                    if event_type == "assistant.message":
                        content_parts.append(getattr(getattr(event, "data", None), "content", ""))
                    elif event_type == "session.idle":
                        done.set()
                    elif event_type in {"error", "session.error", "assistant.error"}:
                        msg = getattr(getattr(event, "data", None), "message", None) or str(getattr(event, "data", ""))
                        error_messages.append(f"{event_type}: {msg}")
                        done.set()

                session.on(on_event)
                await session.send(prompt)
                await done.wait()

                if error_messages:
                    logger.warning(
                        "Copilot SDK returned errors while resolving %s: %s",
                        file_path,
                        "; ".join(error_messages),
                    )
                    return None

                raw = content_parts[-1] if content_parts else ""
                if raw == "":
                    return None

                if raw.startswith("```"):
                    lines = raw.splitlines()
                    if len(lines) >= 3 and lines[0].startswith("```") and lines[-1].strip() == "```":
                        raw = "\n".join(lines[1:-1])
                return raw
            except Exception as exc:  # pragma: no cover - defensive runtime fallback
                logger.warning("Copilot SDK conflict resolution failed for %s: %s", file_path, exc)
                return None
            finally:
                if session is not None:
                    try:
                        await session.disconnect()
                    except Exception:  # pragma: no cover - defensive cleanup
                        pass
                if client is not None:
                    try:
                        await client.stop()
                    except Exception:  # pragma: no cover - defensive cleanup
                        pass

        try:
            return asyncio.run(asyncio.wait_for(_run(), timeout=timeout_seconds))
        except asyncio.TimeoutError:
            logger.warning("Copilot SDK conflict resolution timed out for %s after %ss", file_path, timeout_seconds)
            return None
        except RuntimeError as exc:  # pragma: no cover - defensive runtime fallback
            logger.warning("Copilot SDK conflict resolution could not start event loop for %s: %s", file_path, exc)
            return None

    def _resolve_rebase_conflicts_via_sdk(
        self,
        *,
        base_branch: str,
        head_branch: str,
        max_rounds: int = 5,
    ) -> bool:
        """Best-effort auto-resolution of in-progress rebase conflicts via Copilot SDK."""

        def _has_conflict_markers(content: str) -> bool:
            return bool(re.search(r"(?m)^(<<<<<<<|=======|>>>>>>>)(?: .*)?$", content))

        for round_index in range(max_rounds):
            conflicted_raw = self._run_git(["diff", "--name-only", "--diff-filter=U"])
            conflicted_files = [line.strip() for line in conflicted_raw.splitlines() if line.strip()]
            if not conflicted_files:
                logger.warning("No conflicted files found while attempting rebase conflict resolution.")
                return False

            logger.info(
                "Attempting Copilot SDK conflict resolution for %d file(s) (round %d/%d).",
                len(conflicted_files),
                round_index + 1,
                max_rounds,
            )

            for file_path in conflicted_files:
                path = Path(file_path)
                try:
                    conflict_content = path.read_text(encoding="utf-8")
                except Exception as exc:
                    logger.warning("Failed to read conflicted file %s: %s", file_path, exc)
                    return False

                resolved_content = self._resolve_conflicted_file_content_via_sdk(
                    file_path=file_path,
                    conflict_content=conflict_content,
                    base_branch=base_branch,
                    head_branch=head_branch,
                )
                if resolved_content is None:
                    logger.warning("Copilot SDK did not return a resolution for %s.", file_path)
                    return False

                if _has_conflict_markers(resolved_content):
                    logger.warning(
                        "Copilot SDK returned unresolved conflict markers for %s; refusing to stage.",
                        file_path,
                    )
                    return False

                path.write_text(resolved_content, encoding="utf-8")
                self._run_git(["add", file_path])

            try:
                self._run_git(["rebase", "--continue"])
                logger.info("Rebase conflict resolution completed successfully.")
                return True
            except RuntimeError as exc:
                still_conflicted = self._run_git(["diff", "--name-only", "--diff-filter=U"]).strip()
                if not still_conflicted:
                    logger.warning("`git rebase --continue` failed without remaining conflicts: %s", exc)
                    return False
                logger.warning(
                    "Rebase still has conflicts after SDK resolution round %d: %s",
                    round_index + 1,
                    exc,
                )

        logger.warning("Exceeded maximum conflict-resolution rounds (%d).", max_rounds)
        return False

    def _squash_and_force_push(
        self,
        *,
        base_branch: str,
        head_branch: str,
        head_sha: str,
        reset_to_remote: bool = False,
    ) -> None:
        """Squash commits on head branch into one and force-push with lease."""
        self._run_git(["fetch", "origin", base_branch, head_branch])
        self._run_git(["checkout", head_branch])
        if reset_to_remote:
            self._run_git(["reset", "--hard", f"origin/{head_branch}"])
        merge_base = self._run_git(["merge-base", "HEAD", f"origin/{base_branch}"]).strip()
        commit_count = int(self._run_git(["rev-list", "--count", f"{merge_base}..HEAD"]).strip() or "0")
        if commit_count > 1:
            subjects_raw = self._run_git(["log", "--format=%s", f"{merge_base}..HEAD"])
            commit_subjects = [line for line in subjects_raw.splitlines() if line.strip()]
            commit_message = self._generate_commit_message_via_sdk(
                head_sha=head_sha,
                commit_subjects=commit_subjects,
            ) or self._build_squash_commit_message(head_sha, commit_subjects)
            self._run_git(["reset", "--soft", merge_base])
            self._run_git(["commit", "-m", commit_message])
        rebase_target = f"origin/{base_branch}"
        try:
            logger.info("Rebasing squashed branch onto %s", rebase_target)
            self._run_git(["rebase", rebase_target])
            logger.info("Rebase onto %s completed successfully", rebase_target)
        except RuntimeError as exc:
            logger.warning("Rebase onto %s failed: %s", rebase_target, exc)
            logger.info("Attempting conflict resolution via Copilot SDK while rebase is in progress")
            try:
                resolved = self._resolve_rebase_conflicts_via_sdk(
                    base_branch=base_branch,
                    head_branch=head_branch,
                )
            except RuntimeError as resolve_exc:
                logger.warning("Conflict resolution helper raised: %s", resolve_exc)
                resolved = False
            if not resolved:
                logger.warning(
                    "Could not auto-resolve rebase conflicts. Aborting rebase and proceeding with squashed commit."
                )
                try:
                    self._run_git(["rebase", "--abort"])
                except RuntimeError as abort_exc:
                    raise RuntimeError(f"`git rebase --abort` failed: {abort_exc}") from abort_exc
        self._run_git(["push", "--force-with-lease", "origin", f"HEAD:{head_branch}"])

    def squash_before_publish(
        self,
        *,
        pr_number: int,
        base_branch: str,
        head_branch: str,
        head_sha: str,
    ) -> None:
        """Squash commits and push branch before draft PR publish."""
        logger.info("Squashing PR #%d before publish", pr_number)
        self._squash_and_force_push(base_branch=base_branch, head_branch=head_branch, head_sha=head_sha)

    def count_commits_above_merge_base(
        self,
        *,
        base_branch: str,
        head_sha: str,
    ) -> int:
        """Return commit count above merge-base between origin/base and ``head_sha``."""
        self._run_git(["fetch", "origin", base_branch])
        self._run_git(["fetch", "origin", head_sha])
        merge_base = self._run_git(["merge-base", head_sha, f"origin/{base_branch}"]).strip()
        commit_count_raw = self._run_git(["rev-list", "--count", f"{merge_base}..{head_sha}"]).strip()
        return int(commit_count_raw or "0")

    def _resolve_repo(self) -> str:
        """Resolve the repository in ``owner/repo`` format."""
        repo = self._repo or os.environ.get("GITHUB_REPOSITORY", "")
        if "/" not in repo:
            raise RuntimeError("Repository must be in 'owner/repo' format for post-repair finalization.")
        return repo

    def finalize_post_repair(
        self,
        *,
        pr_number: int,
        base_branch: str,
        head_branch: str,
        head_sha: str,
        review_id: int,
    ) -> None:
        """Perform soft post-repair finalization after Copilot pushes a fix commit.

        Each sub-operation is individually retried so that a transient failure
        partway through does not re-execute already-completed steps (addresses
        the non-idempotent retry concern).

        Delegates thread resolution to the existing ``cli/github`` module to
        avoid duplicating GraphQL pagination and retry logic.
        """
        repo = self._resolve_repo()

        # 1. Reply to each review comment (individually retried via decorator)
        comment_ids = self._list_review_comment_ids(pr_number, review_id)
        addressed_reply_parent_comment_ids = set()
        if comment_ids:
            addressed_reply_parent_comment_ids = self._list_addressed_reply_parent_comment_ids(pr_number)
        for comment_id in comment_ids:
            if self._has_existing_addressed_reply(pr_number, comment_id, addressed_reply_parent_comment_ids):
                continue
            self._reply_to_review_comment(pr_number, comment_id)

        # 2. Resolve threads — delegates to existing resolve_review_threads()
        #    which already handles GraphQL pagination, retry, and verification
        _resolve_review_threads(pr_number, repo, review_id=review_id)

    def squash_post_repair(
        self,
        *,
        pr_number: int,
        base_branch: str,
        head_branch: str,
        head_sha: str,
    ) -> None:
        """Squash post-repair commits and re-request Copilot review.

        Called from the comment-triggered post-repair phase after the
        Copilot coding agent session has completed.
        """
        # 1. Squash and force-push
        self._squash_and_force_push(base_branch=base_branch, head_branch=head_branch, head_sha=head_sha)

        # 1b. Guard against the race where Copilot SWE agent pushes another
        #     commit during finalization — re-fetch and hard-reset to remote
        #     head branch before re-checking commit count.
        self._squash_and_force_push(
            base_branch=base_branch,
            head_branch=head_branch,
            head_sha=head_sha,
            reset_to_remote=True,
        )

        # 2. Ensure PR is published if still draft (edge-case safety)
        pr_meta = self.get_pr_metadata(pr_number)
        if pr_meta.is_draft:
            self.publish_pr(pr_number)

        # 3. Re-request Copilot review — delegates to existing module which
        #    handles POST + exponential backoff verification + reviews fallback
        repo = self._resolve_repo()
        _request_copilot_review(pr_number, repo)
