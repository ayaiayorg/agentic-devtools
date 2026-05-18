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
from agentic_devtools.cli.github.request_copilot_review import request_copilot_review as _request_copilot_review
from agentic_devtools.cli.github.resolve_review_threads import resolve_review_threads as _resolve_review_threads
from agentic_devtools.cli.subprocess_utils import run_safe

logger = logging.getLogger(__name__)


def _build_repair_comment(
    *,
    head_sha: str,
    repair_type: str,
    failed_checks: list[CheckRunStatus],
    review_comments: list[str],
    repository_full_name: str = "",
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
        review_comments: List of review comment bodies (for review repair context).

    Returns:
        Comment body string beginning with ``@copilot``.
    """
    parts: list[str] = ["@copilot"]

    if repair_type in ("review", "both") and review_comments:
        parts.append("")
        parts.append("## Copilot Review Feedback")
        parts.append("")
        parts.append(
            "Please address the following review comments. "
            "For each comment, make the necessary code changes, "
            "then reply to the comment explaining what you changed "
            "and resolve the thread."
        )
        for i, comment in enumerate(review_comments, 1):
            parts.append("")
            parts.append(f"### Comment {i}")
            parts.append("")
            # Quote the original review comment
            quoted = "\n".join(f"> {line}" for line in comment.splitlines())
            parts.append(quoted)

    if repair_type in ("ci", "both") and failed_checks:
        parts.append("")
        parts.append("## CI Failure Context")
        parts.append("")
        parts.append(
            "The following CI checks have failed. Please fix the issues "
            "described below. Use `ruff check --fix .` and `ruff format .` "
            "for lint/format failures."
        )
        for check in failed_checks:
            parts.append("")
            parts.append(f"### ❌ {check.name}")
            parts.append(f"- **Conclusion**: {check.conclusion}")
            if repository_full_name and "/" in repository_full_name:
                parts.append(f"- **Job**: https://github.com/{repository_full_name}/runs/{check.id}")

    if not review_comments and not failed_checks:
        parts.append("")
        parts.append(f"Please review the PR and fix any issues found. Current HEAD: `{head_sha[:8]}`.")

    parts.append("")
    parts.append("---")
    parts.append(f"*Automated repair dispatch for commit `{head_sha[:8]}` (type: {repair_type})*")

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
        review_comments: list[str],
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
    def list_review_comments(self, pr_number: int, review_id: int) -> list[str]:
        """List inline comments from a specific review."""
        response = _gh_api(
            self._repo_api(f"/pulls/{pr_number}/reviews/{review_id}/comments"),
            paginate=True,
        )
        comments = _parse_paginated_json(response)
        return [c.get("body", "") for c in comments]

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
    def _reply_to_review_comment(self, pr_number: int, comment_id: int, head_sha: str) -> None:
        """Post addressed reply to a single review comment."""
        _gh_api(
            self._repo_api(f"/pulls/{pr_number}/comments/{comment_id}/replies"),
            method="POST",
            body={"body": f"Addressed by fix commit `{head_sha[:8]}`."},
        )

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

    def _squash_and_force_push(self, *, base_branch: str, head_branch: str, head_sha: str) -> None:
        """Squash commits on head branch into one and force-push with lease."""
        self._run_git(["fetch", "origin", base_branch, head_branch])
        self._run_git(["checkout", head_branch])
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
        """Finalize a post-repair cycle after Copilot pushes a fix commit.

        Each sub-operation is individually retried so that a transient failure
        partway through does not re-execute already-completed steps (addresses
        the non-idempotent retry concern).

        Delegates thread resolution and Copilot re-request to the existing
        ``cli/github`` modules to avoid duplicating GraphQL pagination,
        verification, and retry logic.
        """
        repo = self._resolve_repo()

        # 1. Reply to each review comment (individually retried via decorator)
        comment_ids = self._list_review_comment_ids(pr_number, review_id)
        for comment_id in comment_ids:
            self._reply_to_review_comment(pr_number, comment_id, head_sha)

        # 2. Resolve threads — delegates to existing resolve_review_threads()
        #    which already handles GraphQL pagination, retry, and verification
        _resolve_review_threads(pr_number, repo, review_id=review_id)

        # 3. Squash and force-push
        self._squash_and_force_push(base_branch=base_branch, head_branch=head_branch, head_sha=head_sha)

        # 4. Ensure PR is published if still draft (edge-case safety)
        pr_meta = self.get_pr_metadata(pr_number)
        if pr_meta.is_draft:
            self.publish_pr(pr_number)

        # 5. Re-request Copilot review — delegates to existing module which
        #    handles POST + exponential backoff verification + reviews fallback
        _request_copilot_review(pr_number, repo)
