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
from typing import Any, cast

from agentic_devtools.cli.ci.exceptions import MalformedEventError
from agentic_devtools.cli.ci.models import (
    CheckRunStatus,
    CommentResolution,
    EventPayload,
    FinalizationResult,
    IssueCommentInfo,
    IssueEvent,
    PRMetadata,
    ReviewCommentInfo,
    ReviewInfo,
    VerificationVerdict,
)
from agentic_devtools.cli.ci.provider import CIPlatformProvider
from agentic_devtools.cli.ci.resolution.engine import TieredResolutionEngine
from agentic_devtools.cli.ci.resolution.github_adapter import (
    GitHubResolutionContext,
    GitHubReviewThread,
    GitHubThreadComment,
)
from agentic_devtools.cli.ci.resolution.models import ResolutionVerdict, ThreadResolutionState, TierResult
from agentic_devtools.cli.ci.resolution.protocols import EvaluationTier, ResolutionContext, ReviewThread
from agentic_devtools.cli.ci.resolution.reply_formatter import ReplyFormatter
from agentic_devtools.cli.ci.resolution.state_persistence import (
    clear_resolution_state,
    increment_iteration,
    is_tentative_expired,
    load_resolution_state,
    mark_abandoned,
    save_resolution_state,
)
from agentic_devtools.cli.ci.resolution.tiers.automation_markers import AutomationMarkerTier
from agentic_devtools.cli.ci.resolution.tiers.outdated import OutdatedTier
from agentic_devtools.cli.ci.resolution.tiers.sdk_evaluation import SdkEvaluationTier
from agentic_devtools.cli.ci.retry import RetryableError, retry_with_backoff
from agentic_devtools.cli.github.request_copilot_review import request_copilot_review as _request_copilot_review
from agentic_devtools.cli.github.resolve_review_threads import (
    resolve_review_threads as _resolve_review_threads,
)
from agentic_devtools.cli.github.resolve_review_threads import (
    unresolve_review_threads as _unresolve_review_threads,
)
from agentic_devtools.cli.subprocess_utils import run_safe
from agentic_devtools.state import get_state_dir

logger = logging.getLogger(__name__)

_ADDRESSED_REPLY_BODY = "Addressed on the updated PR branch."
_LEGACY_ADDRESSED_REPLY_PREFIXES = ("addressed by fix commit",)
_RESOLUTION_TIER_MARKER_PREFIX = "<!-- agdt:resolution-tier:"
_RESOLUTION_TIER_ABANDONED_MARKER = "<!-- agdt:resolution-tier:abandoned -->"
_RESOLUTION_UNCONFIRMED_MARKER = "<!-- agdt:resolution-tier:unconfirmed-commit-change -->"
_RESOLUTION_THREAD_RESOLVED_TEXT = "**thread resolved**"
_RESOLUTION_THREAD_LEFT_OPEN_TEXT = "**thread left open**"
_THREAD_RESOLUTION_STATE_DIRNAME = "thread-resolution"
_REVIEW_THREADS_QUERY = """
query($owner: String!, $repoName: String!, $prNumber: Int!, $threadsCursor: String) {
  repository(owner: $owner, name: $repoName) {
    pullRequest(number: $prNumber) {
      reviewThreads(first: 100, after: $threadsCursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          isResolved
          isOutdated
          path
          line
          startLine
          comments(first: 100) {
            nodes {
              databaseId
              body
              createdAt
              author { login }
              commit { oid }
            }
          }
        }
      }
    }
  }
}
"""


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


# ---------------------------------------------------------------------------
# Suppressed-comment recovery from Copilot review body
# ---------------------------------------------------------------------------

# Regex to extract the <details> block containing suppressed comments.
# Uses DOTALL so `.*?` spans newlines.
_SUPPRESSED_DETAILS_RE = re.compile(
    r"<details>\s*<summary>[^<]*suppressed due to low confidence[^<]*</summary>(.*?)</details>",
    re.DOTALL | re.IGNORECASE,
)

# Regex to extract individual entries within the suppressed block.
# Each entry starts with a bold or code-formatted file path, followed by body text.
# Matches patterns like:
#   **path/to/file.py**: body text
#   `path/to/file.py`: body text
#   **`path/to/file.py`**: body text
_SUPPRESSED_ENTRY_RE = re.compile(
    r"(?:\*\*`?|`)"  # opening bold/code marker
    r"([^`*\n]+?)"  # file path (captured)
    r"(?:`?\*\*|`)"  # closing bold/code marker
    r"\s*:?\s*"  # optional colon separator
    r"(.*?)(?=\n(?:\*\*`?|`)[^`*\n]+?(?:`?\*\*|`)\s*:?|\Z)",  # body (captured, up to next entry or end)
    re.DOTALL,
)


def _parse_suppressed_from_review_body(review_body: str) -> list[ReviewCommentInfo]:
    """Parse suppressed comments from a Copilot review body HTML.

    Extracts comments from the ``<details>`` block with summary containing
    "suppressed due to low confidence". Each entry is expected to have a bold
    or code-formatted file path followed by comment body text.

    Args:
        review_body: Full review body text (may contain HTML).

    Returns:
        List of ``ReviewCommentInfo`` with ``is_suppressed=True`` and negative
        sentinel IDs. Returns empty list if no suppressed block is found.
    """
    if not review_body:
        return []

    match = _SUPPRESSED_DETAILS_RE.search(review_body)
    if not match:
        return []

    block_content = match.group(1).strip()
    if not block_content:
        return []

    entries: list[ReviewCommentInfo] = []
    sentinel_id = -1

    for entry_match in _SUPPRESSED_ENTRY_RE.finditer(block_content):
        path = entry_match.group(1).strip()
        body = entry_match.group(2).strip()

        if not path:
            path = "(unknown file)"
        if not body:
            continue

        entries.append(
            ReviewCommentInfo(
                id=sentinel_id,
                path=path,
                body=body,
                html_url="",
                is_suppressed=True,
            )
        )
        sentinel_id -= 1

    # If we found a details block but no structured entries, try a line-based
    # fallback: treat each non-empty line as a standalone comment.
    if not entries:
        for line in block_content.splitlines():
            line = line.strip()
            if not line:
                continue
            entries.append(
                ReviewCommentInfo(
                    id=sentinel_id,
                    path="(unknown file)",
                    body=line,
                    html_url="",
                    is_suppressed=True,
                )
            )
            sentinel_id -= 1

    return entries


def _deduplicate_review_comments(
    rest_comments: list[ReviewCommentInfo],
    suppressed_comments: list[ReviewCommentInfo],
) -> list[ReviewCommentInfo]:
    """Merge REST and suppressed comments, removing exact duplicates.

    When a suppressed comment matches a REST comment (after path and body
    normalization), the REST entry is preserved and the suppressed duplicate
    is dropped.

    Args:
        rest_comments: Comments from the REST API (non-suppressed).
        suppressed_comments: Synthetic comments parsed from the review body.

    Returns:
        Merged list: all REST comments followed by non-duplicate suppressed ones.
    """
    if not suppressed_comments:
        return list(rest_comments)

    def _normalize_path(path: str) -> str:
        p = path.strip()
        if p.startswith("/"):
            p = p[1:]
        return p

    def _normalize_body(body: str) -> str:
        return body.replace("\r\n", "\n").strip()

    rest_keys: set[tuple[str, str]] = set()
    for c in rest_comments:
        rest_keys.add((_normalize_path(c.path), _normalize_body(c.body)))

    filtered: list[ReviewCommentInfo] = []
    for c in suppressed_comments:
        key = (_normalize_path(c.path), _normalize_body(c.body))
        if key not in rest_keys:
            filtered.append(c)

    return list(rest_comments) + filtered


def _is_transient_gh_failure(stderr: str) -> bool:
    """Return True when stderr indicates a retryable transient GitHub/CLI failure."""
    stderr_lower = stderr.lower()
    if "rate limit" in stderr_lower or "secondary rate limit" in stderr_lower:
        return True
    return bool(re.search(r"\b(?:http|status(?: code)?)\D*(429|500|502|503|504)\b", stderr_lower))


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

    Output uses collapsible ``<details>`` blocks to keep PR page real estate
    compact while still providing full context on expansion.

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
    has_review = repair_type in ("review", "both")
    has_review_comments = has_review and bool(review_comments)
    has_ci = repair_type in ("ci", "both") and bool(failed_checks)

    # --- First line: @copilot with inline summary ---
    review_url = ""
    if has_review and review_id and repository_full_name and "/" in repository_full_name and pr_number:
        review_url = f"https://github.com/{repository_full_name}/pull/{pr_number}#pullrequestreview-{review_id}"

    if has_review and review_url:
        parts: list[str] = [
            f"@copilot - The Code Review Agent just left this [Review]({review_url})"
            " that needs to be evaluated and addressed."
        ]
    elif has_ci:
        parts = ["@copilot - CI failures detected that need to be addressed."]
    else:
        parts = ["@copilot"]

    # --- Dedup marker ---
    if has_review and review_id:
        parts.append("")
        parts.append(f"<!-- copilot-trigger:{review_id} -->")

    # --- Fallback for empty context ---
    has_review_context = has_review and bool(review_id)
    if not review_comments and not failed_checks and not has_review_context:
        parts.append("")
        parts.append(f"Please review the PR and fix any issues found. Current HEAD: `{head_sha[:8]}`.")
        parts.append("")
        parts.append("---")
        parts.append(f"*Automated repair dispatch for commit `{head_sha[:8]}` (type: {repair_type})*")
        return "\n".join(parts)

    # --- Instructions <details> block ---
    if repair_type == "ci":
        skill = "agdt.address-copilot-review.ci-repair.agent.md"
        prompt_skill = "agdt.address-copilot-review.ci-repair.prompt.md"
    else:
        skill = "agdt.address-copilot-review.evaluate-and-respond.agent.md"
        prompt_skill = "agdt.address-copilot-review.evaluate-and-respond.prompt.md"

    if repository_full_name and "/" in repository_full_name:
        agent_url = f"https://github.com/{repository_full_name}/blob/main/.github/agents/{skill}"
        prompt_url = f"https://github.com/{repository_full_name}/blob/main/.github/prompts/{prompt_skill}"
        agent_link = f"[`.github/agents/{skill}`]({agent_url})"
        prompt_link = f"[`.github/prompts/{prompt_skill}`]({prompt_url})"
    else:
        agent_link = f"`.github/agents/{skill}`"
        prompt_link = f"`.github/prompts/{prompt_skill}`"

    parts.append("")
    parts.append("<details>")
    parts.append("     <summary>Instructions</summary>")
    parts.append("")
    parts.append(f"You are an {agent_link} agent, your prompt can be found here: {prompt_link}.")
    parts.append("")
    parts.append("</details>")

    # --- Comments <details> block ---
    if has_review_comments:
        parts.append("")
        parts.append("<details>")
        parts.append("     <summary>Comments</summary>")
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
                parts.append(f'- `Comment #{nc}` - `{filename} ({nf})`: "{body}" (suppressed comment)')
            else:
                label = f"Comment #{nc} - {filename} ({nf})"
                if comment.html_url:
                    parts.append(f"- [{label}]({comment.html_url})")
                else:
                    parts.append(f"- {label}")

        parts.append("</details>")

    # --- CI Failures <details> block ---
    if has_ci:
        parts.append("")
        parts.append("<details>")
        parts.append("     <summary>CI Failures</summary>")
        parts.append("")
        for check in failed_checks:
            job_url = check.html_url
            if job_url:
                parts.append(f"- ❌ [{check.name}]({job_url}) — `{check.conclusion}`")
            else:
                parts.append(f"- ❌ {check.name} — `{check.conclusion}`")
        parts.append("</details>")

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
            else:  # pragma: no cover
                pass
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
        self._thread_signals_cache: dict[int, dict[int, tuple[bool | None, str]]] = {}

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
            if event_name == "workflow_dispatch":
                return self._parse_workflow_dispatch_event(raw_payload)
        except (KeyError, TypeError) as exc:
            raise MalformedEventError(event_name, str(exc)) from exc

        raise MalformedEventError(event_name, f"unsupported event type: {event_name}")

    def _parse_pull_request_event(self, raw: dict) -> EventPayload:
        pr = raw["pull_request"]
        action = raw.get("action", "")

        # Detect edit-change metadata for edited events
        title_changed = False
        body_changed = False
        base_changed = False
        edit_changes_known = False
        changes = raw.get("changes")
        if action == "edited" and isinstance(changes, dict):
            edit_changes_known = True
            title_changed = "title" in changes
            body_changed = "body" in changes
            base_changed = "base" in changes

        return EventPayload(
            pr_number=pr["number"],
            head_branch=pr["head"]["ref"],
            head_sha=pr["head"]["sha"],
            base_branch=pr["base"]["ref"],
            action=action,
            repository_full_name=raw.get("repository", {}).get("full_name", ""),
            sender_login=raw.get("sender", {}).get("login", ""),
            title_changed=title_changed,
            body_changed=body_changed,
            base_changed=base_changed,
            edit_changes_known=edit_changes_known,
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

    def _parse_workflow_dispatch_event(self, raw: dict) -> EventPayload:
        """Parse a workflow_dispatch event, extracting pr_number from inputs.

        Treats the dispatch as equivalent to a ``workflow_run`` completion event
        (action="completed") so the orchestrator routes it to the squash-wait path.
        """
        inputs = raw.get("inputs") or {}
        pr_number_str = str(inputs.get("pr_number", "") or "").strip()
        try:
            pr_number = int(pr_number_str) if pr_number_str else 0
        except (ValueError, TypeError):
            pr_number = 0
        return EventPayload(
            pr_number=pr_number,
            action="completed",
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
    def list_issue_comments(self, pr_number: int) -> list[IssueCommentInfo]:
        """List PR issue comments ordered by API response order."""
        response = _gh_api(self._repo_api(f"/issues/{pr_number}/comments"), paginate=True)
        comments = _parse_paginated_json(response)
        return [
            IssueCommentInfo(
                id=int(comment.get("id", 0)),
                author=(comment.get("user") or {}).get("login", ""),
                body=comment.get("body", "") or "",
                created_at=comment.get("created_at", "") or "",
            )
            for comment in comments
            if comment.get("id")
        ]

    @retry_with_backoff()
    def list_review_thread_states(self, pr_number: int) -> dict[int, tuple[bool, bool]]:
        """Return review comment -> (is_resolved, has_reply) mapping via GraphQL threads."""
        owner, repo_name = self._resolve_repo().split("/", maxsplit=1)
        cursor: str | None = None
        status_map: dict[int, tuple[bool, bool]] = {}

        while True:
            variables: dict[str, Any] = {
                "owner": owner,
                "repoName": repo_name,
                "prNumber": pr_number,
            }
            if cursor is not None:
                variables["threadsCursor"] = cursor
            response = _gh_api(
                "graphql",
                method="POST",
                body={"query": _REVIEW_THREADS_QUERY, "variables": variables},
            )
            data = json.loads(response)
            thread_data = data["data"]["repository"]["pullRequest"]["reviewThreads"]
            for thread in thread_data.get("nodes", []):
                is_resolved = bool(thread.get("isResolved", False))
                comment_nodes = thread.get("comments", {}).get("nodes", [])
                has_reply = len(comment_nodes) > 1
                for node in comment_nodes:
                    comment_id = node.get("databaseId")
                    if isinstance(comment_id, int):
                        status_map[comment_id] = (is_resolved, has_reply)

            page_info = thread_data.get("pageInfo", {})
            if page_info.get("hasNextPage") is True and page_info.get("endCursor"):
                cursor = page_info["endCursor"]
            else:
                break

        return status_map

    @retry_with_backoff()
    def _fetch_thread_signals_by_comment_id(self, pr_number: int) -> dict[int, tuple[bool | None, str]]:
        """Return thread-level signals keyed by review comment databaseId.

        Maps each review comment ID to:
        - thread isOutdated status
        - latest thread comment body (used by automation-marker tier)
        """
        cached = self._thread_signals_cache.get(pr_number)
        if cached is not None:
            return cached

        owner, repo_name = self._resolve_repo().split("/", maxsplit=1)
        cursor: str | None = None
        result: dict[int, tuple[bool | None, str]] = {}

        while True:
            variables: dict[str, Any] = {
                "owner": owner,
                "repoName": repo_name,
                "prNumber": pr_number,
            }
            if cursor is not None:
                variables["threadsCursor"] = cursor
            response = _gh_api(
                "graphql",
                method="POST",
                body={"query": _REVIEW_THREADS_QUERY, "variables": variables},
            )
            data = json.loads(response)
            thread_data = data["data"]["repository"]["pullRequest"]["reviewThreads"]
            for thread in thread_data.get("nodes", []):
                is_outdated: bool | None = thread.get("isOutdated")
                comment_nodes = thread.get("comments", {}).get("nodes", [])
                latest_comment_body = ""
                if comment_nodes:
                    latest_comment_body = str(comment_nodes[-1].get("body") or "")
                for node in comment_nodes:
                    comment_id = node.get("databaseId")
                    if isinstance(comment_id, int):
                        result[comment_id] = (is_outdated, latest_comment_body)

            page_info = thread_data.get("pageInfo", {})
            if page_info.get("hasNextPage") is True and page_info.get("endCursor"):
                cursor = page_info["endCursor"]
            else:
                break

        self._thread_signals_cache[pr_number] = result
        return result

    @retry_with_backoff()
    def _fetch_outdated_by_comment_id(self, pr_number: int) -> dict[int, bool | None]:
        """Return isOutdated status per comment databaseId via GraphQL thread query."""
        signals = self._fetch_thread_signals_by_comment_id(pr_number)
        return {comment_id: is_outdated for comment_id, (is_outdated, _latest_body) in signals.items()}

    @retry_with_backoff()
    def _fetch_latest_thread_comment_body_by_comment_id(self, pr_number: int) -> dict[int, str]:
        """Return the latest thread comment body per review comment databaseId."""
        signals = self._fetch_thread_signals_by_comment_id(pr_number)
        return {comment_id: latest_body for comment_id, (_is_outdated, latest_body) in signals.items()}

    @retry_with_backoff()
    def approve_pr(self, pr_number: int, head_sha: str, body: str) -> bool:
        """Approve a pull request.

        Uses ``AGDT_PR_APPROVER_PAT`` when set so that the approval comes from
        a separate identity (GitHub prevents approving your own PR).  When the
        variable is unset or empty the approval is skipped with a warning.

        Returns:
            ``True`` when approval was submitted, ``False`` when skipped.
        """
        approver_token = os.environ.get("AGDT_PR_APPROVER_PAT", "").strip()
        if not approver_token:
            logger.warning(
                "AGDT_PR_APPROVER_PAT is not configured. "
                "Cannot approve PR without a dedicated approver token. "
                "See repository documentation for setup instructions."
            )
            return False

        try:
            _gh_api(
                self._repo_api(f"/pulls/{pr_number}/reviews"),
                method="POST",
                body={"commit_id": head_sha, "event": "APPROVE", "body": body},
                token=approver_token,
            )
            return True
        except RuntimeError as exc:
            stderr = str(exc)
            if "401" in stderr or "Bad credentials" in stderr.lower():
                logger.warning(
                    "AGDT_PR_APPROVER_PAT authentication failed (401). "
                    "The token may be expired or invalid. "
                    "Skipping PR approval. Rotate the secret and retry."
                )
                return False
            raise

    @retry_with_backoff()
    def merge_pr(self, pr_number: int, head_sha: str, method: str, *, commit_title: str | None = None) -> None:
        """Merge a pull request.

        ``commit_title`` maps to GitHub's ``commit_title`` field, so it only
        controls the squash commit subject line.
        """
        body: dict[str, str] = {"sha": head_sha, "merge_method": method}
        if commit_title and method == "squash":
            body["commit_title"] = commit_title
        _gh_api(
            self._repo_api(f"/pulls/{pr_number}/merge"),
            method="PUT",
            body=body,
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
        """List inline comments from a specific review.

        After fetching REST inline comments, also recovers suppressed comments
        from the review body ``<details>`` block (when ``review_id > 0``).
        Suppressed comments are deduplicated against REST comments and merged
        into the result with ``is_suppressed=True``.
        """
        response = _gh_api(
            self._repo_api(f"/pulls/{pr_number}/reviews/{review_id}/comments"),
            paginate=True,
        )
        comments = _parse_paginated_json(response)
        rest_comments = [
            ReviewCommentInfo(
                id=int(c["id"]),
                path=c.get("path", ""),
                body=c.get("body", ""),
                html_url=c.get("html_url", ""),
                is_suppressed=_comment_is_suppressed(c),
                start_line=c.get("start_line") if c.get("start_line") is not None else c.get("line"),
                end_line=c.get("line"),
                line=c.get("line"),
                position=c.get("position"),
                diff_hunk=c.get("diff_hunk", ""),
                commit_id=c.get("commit_id", ""),
            )
            for c in comments
        ]

        # Recover suppressed comments from the review body (FR-001, FR-006, FR-008)
        if review_id > 0:
            try:
                review_response = _gh_api(
                    self._repo_api(f"/pulls/{pr_number}/reviews/{review_id}"),
                )
                review_data = json.loads(review_response)
                review_body = review_data.get("body", "") or ""
                suppressed = _parse_suppressed_from_review_body(review_body)
                if suppressed:
                    rest_comments = _deduplicate_review_comments(rest_comments, suppressed)
            except Exception:
                logger.warning(
                    "PR #%d: Failed to recover suppressed comments from review %d body",
                    pr_number,
                    review_id,
                )

        return rest_comments

    @retry_with_backoff()
    def list_pr_issue_events(self, pr_number: int) -> list[IssueEvent]:
        """List Copilot session events for a pull request from the Issues Events API.

        Calls ``GET /repos/{owner}/{repo}/issues/{pr_number}/events`` with
        pagination and returns only Copilot session events
        (copilot_work_finished, copilot_work_finished_failure, copilot_work_started)
        in ascending chronological order.
        """
        from agentic_devtools.cli.ci.models import _COPILOT_SESSION_EVENTS  # noqa: PLC0415

        response = _gh_api(self._repo_api(f"/issues/{pr_number}/events"), paginate=True)
        raw_events = _parse_paginated_json(response)
        events: list[IssueEvent] = []
        for ev in raw_events:
            event_type = ev.get("event", "")
            if event_type not in _COPILOT_SESSION_EVENTS:
                continue
            actor = ev.get("actor") or {}
            events.append(
                IssueEvent(
                    id=int(ev.get("id", 0)),
                    event=event_type,
                    created_at=ev.get("created_at", ""),
                    actor_login=actor.get("login", "") if isinstance(actor, dict) else "",
                )
            )
        events.sort(key=lambda e: e.id)
        return events

    @retry_with_backoff()
    def get_pr_diff(self, pr_number: int) -> str:
        """Get the unified diff for a pull request via ``gh pr diff``."""
        result = run_safe(
            ["gh", "pr", "diff", str(pr_number), "--repo", self._repo],
            capture_output=True,
            text=True,
            shell=False,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip()
            if _is_transient_gh_failure(stderr):
                raise RetryableError(f"gh pr diff failed: {stderr}")
            raise RuntimeError(f"gh pr diff failed: {stderr}")
        return result.stdout

    @retry_with_backoff()
    def get_commit_range_diff(self, base_sha: str, head_sha: str) -> str:
        """Get unified diff for ``base_sha...head_sha`` via GitHub compare API."""
        result = run_safe(
            [
                "gh",
                "api",
                self._repo_api(f"/compare/{base_sha}...{head_sha}"),
                "--method",
                "GET",
                "-H",
                "Accept: application/vnd.github.v3.diff",
            ],
            capture_output=True,
            text=True,
            shell=False,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip()
            if _is_transient_gh_failure(stderr):
                raise RetryableError(f"gh api compare diff failed: {stderr}")
            raise RuntimeError(f"gh api compare diff failed: {stderr}")
        return result.stdout

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
    def _reply_to_review_comment(self, pr_number: int, comment_id: int, body: str = _ADDRESSED_REPLY_BODY) -> None:
        """Post addressed reply to a single review comment."""
        _gh_api(
            self._repo_api(f"/pulls/{pr_number}/comments/{comment_id}/replies"),
            method="POST",
            body={"body": body},
        )

    @retry_with_backoff()
    def _list_addressed_reply_parent_comment_ids(self, pr_number: int) -> set[int]:
        """Return parent comment IDs that already have an addressed reply.

        Structured resolution-tier replies are considered addressed only when they
        indicate a resolved outcome, so tentative/abandoned lifecycle replies do
        not suppress the final resolved audit reply.
        """
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
                or (
                    _RESOLUTION_TIER_MARKER_PREFIX in str(comment.get("body", ""))
                    and _RESOLUTION_THREAD_RESOLVED_TEXT in str(comment.get("body", "")).strip().lower()
                )
            )
        }

    @retry_with_backoff()
    def _list_abandoned_reply_parent_comment_ids(self, pr_number: int) -> set[int]:
        """Return parent comment IDs that already have an abandoned-resolution reply.

        Unlike :meth:`_list_addressed_reply_parent_comment_ids`, this method only
        matches the specific abandoned marker so that an earlier tentative-resolution
        reply does not suppress the abandoned notification on TTL expiry.
        """
        response = _gh_api(
            self._repo_api(f"/pulls/{pr_number}/comments"),
            paginate=True,
        )
        comments = _parse_paginated_json(response)
        return {
            int(comment["in_reply_to_id"])
            for comment in comments
            if comment.get("in_reply_to_id") and _RESOLUTION_TIER_ABANDONED_MARKER in str(comment.get("body", ""))
        }

    @retry_with_backoff()
    def _list_unresolve_reply_parent_comment_ids(self, pr_number: int) -> set[int]:
        """Return parent comment IDs that already have a 'Thread left open' reply.

        Used to prevent posting duplicate UNRESOLVE audit replies on the same
        thread across repeated AI PR Loop runs.  Only replies that contain both
        the resolution-tier HTML marker and the "Thread left open" status text
        are matched; tentative or resolved tier replies are excluded.
        """
        response = _gh_api(
            self._repo_api(f"/pulls/{pr_number}/comments"),
            paginate=True,
        )
        comments = _parse_paginated_json(response)
        return {
            int(comment["in_reply_to_id"])
            for comment in comments
            if comment.get("in_reply_to_id")
            and _RESOLUTION_TIER_MARKER_PREFIX in str(comment.get("body", ""))
            and _RESOLUTION_THREAD_LEFT_OPEN_TEXT in str(comment.get("body", "")).strip().lower()
        }

    @retry_with_backoff()
    def _list_unconfirmed_resolved_comment_ids(self, pr_number: int) -> set[int]:
        """Return parent comment IDs that have an unconfirmed-commit-change marker reply.

        These threads were resolved by default because HEAD changed but the SDK
        could not confirm resolution. They are eligible for re-evaluation on
        subsequent loop iterations.
        """
        response = _gh_api(
            self._repo_api(f"/pulls/{pr_number}/comments"),
            paginate=True,
        )
        comments = _parse_paginated_json(response)
        # Only treat a thread as unconfirmed when the *latest* reply on that parent contains the marker.
        # Determine "latest" by created_at to avoid relying on API ordering.
        latest_reply_by_parent: dict[int, dict] = {}
        for comment in comments:
            parent_id = comment.get("in_reply_to_id")
            if parent_id is None:
                continue
            pid = int(parent_id)
            created_at = str(comment.get("created_at", ""))
            prev = latest_reply_by_parent.get(pid)
            prev_created_at = str(prev.get("created_at", "")) if prev is not None else ""
            if prev is None or prev_created_at <= created_at:
                latest_reply_by_parent[pid] = comment
        return {
            parent_id
            for parent_id, comment in latest_reply_by_parent.items()
            if _RESOLUTION_UNCONFIRMED_MARKER in str(comment.get("body", ""))
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

    def _fetch_review_comment_by_id(self, pr_number: int, comment_id: int) -> ReviewCommentInfo | None:
        """Fetch a single review comment by its ID for re-evaluation purposes."""
        try:
            response = _gh_api(
                self._repo_api(f"/pulls/comments/{comment_id}"),
            )
            c = json.loads(response)
            return ReviewCommentInfo(
                id=int(c["id"]),
                path=c.get("path", ""),
                body=c.get("body", ""),
                html_url=c.get("html_url", ""),
                is_suppressed=_comment_is_suppressed(c),
                start_line=c.get("start_line") if c.get("start_line") is not None else c.get("line"),
                end_line=c.get("line"),
                line=c.get("line"),
                position=c.get("position"),
                diff_hunk=c.get("diff_hunk", ""),
                commit_id=c.get("commit_id", ""),
            )
        except Exception as exc:
            logger.warning(
                "Failed to fetch review comment %d for PR #%d: %s",
                comment_id,
                pr_number,
                exc,
            )
            return None

    def _resolution_state_dir(self) -> Path:
        """Return the state directory for tentative thread lifecycle tracking."""
        return get_state_dir() / _THREAD_RESOLUTION_STATE_DIRNAME

    @staticmethod
    def _model_id_for_tier_result(result: TierResult) -> str | None:
        if result.tier_name == "sdk_evaluation":
            return os.environ.get("COPILOT_MODEL", "claude-opus-4.6")
        if result.tier_name == "sdk_evaluation_fallback":
            return os.environ.get("COPILOT_FALLBACK_MODEL", "claude-sonnet-4.6")
        return None

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
                    else:  # pragma: no cover
                        pass

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
                else:  # pragma: no cover
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
                    else:  # pragma: no cover
                        pass

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
                else:  # pragma: no cover
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
    ) -> FinalizationResult:
        """Perform soft post-repair finalization after Copilot pushes a fix commit.

        Implements commit-change guard and per-comment SDK verification:
        1. Fetches the review to get its commit_sha.
        2. Guards: skips if no new commit since the review (FR-001/002).
        3. For each unresolved comment, calls the Copilot SDK to verify
           whether the diff addresses the feedback (FR-004/005/006/007).
        4. Only replies and resolves threads where SDK responds COMMENT_RESOLVE.

        Returns:
            FinalizationResult with details about what was resolved/skipped.
        """
        repo = self._resolve_repo()
        self._thread_signals_cache.pop(pr_number, None)

        # --- Commit Guard (FR-001/002/014) ---
        reviews = self.list_reviews(pr_number)
        review = next((r for r in reviews if r.id == review_id), None)

        # FR-014: null/missing review or commit_sha → fail-safe skip
        if not review or not review.commit_sha:
            logger.error(
                "Cannot determine review commit SHA for review %d on PR #%d — skipping finalization (fail-safe)",
                review_id,
                pr_number,
            )
            return FinalizationResult(skipped=True, reason="unresolvable_review_commit_sha")

        # FR-001/002: no new commit since review → skip
        if review.commit_sha == head_sha:
            logger.warning(
                "No new commit since Copilot review %d on PR #%d (both at %s) — skipping finalization",
                review_id,
                pr_number,
                head_sha,
            )
            return FinalizationResult(skipped=True, reason="no_new_commit")

        # --- Per-Comment SDK Verification Loop (FR-004/005/006/007/008) ---
        comments = self.list_review_comments(pr_number, review_id)
        if not comments:
            logger.info("No review comments for review %d on PR #%d — nothing to finalize", review_id, pr_number)
            return FinalizationResult(skipped=False, reason="no_comments")

        # Build diff context once for this review
        diff_context = self._build_verification_context_diff(review.commit_sha, head_sha)

        resolved_ids: list[int] = []
        unconfirmed_unresolve_ids: list[int] = []
        resolutions: list[CommentResolution] = []
        errors: list[str] = []

        # Check which comments already have addressed replies so we can avoid
        # duplicate replies while still requiring SDK verification before
        # resolving their threads.
        addressed_reply_parent_comment_ids = self._list_addressed_reply_parent_comment_ids(pr_number)
        # Narrower check for abandoned replies: only suppress the abandoned notification
        # if an abandoned-specific marker already exists. An earlier tentative reply with
        # a different resolution-tier marker must NOT suppress the TTL-expiry notification.
        abandoned_reply_parent_comment_ids = self._list_abandoned_reply_parent_comment_ids(pr_number)
        # Suppress duplicate "Thread left open" audit replies for threads that were
        # already evaluated as UNRESOLVE in a prior AI PR Loop run.
        unresolve_reply_parent_comment_ids = self._list_unresolve_reply_parent_comment_ids(pr_number)

        comments_for_sdk: list[tuple[ReviewCommentInfo, str]] = []
        for comment in comments:
            # Suppressed comments are intentionally left unresolved, but must still
            # be recorded so result counts/summaries reflect remaining open threads.
            if comment.is_suppressed:
                resolutions.append(
                    CommentResolution(
                        comment_id=comment.id,
                        verdict=VerificationVerdict.COMMENT_UNRESOLVE,
                    )
                )
                continue

            comment_context = self._build_comment_verification_context(comment, diff_context)
            comments_for_sdk.append((comment, comment_context))

        # Include previously unconfirmed-resolved threads for re-evaluation
        existing_comment_ids = {comment.id for comment, _ in comments_for_sdk}
        reevaluated_unconfirmed_comment_ids: set[int] = set()
        try:
            unconfirmed_ids = self._list_unconfirmed_resolved_comment_ids(pr_number)
        except Exception as exc:
            logger.warning(
                "Failed to fetch unconfirmed resolved comment IDs for PR #%d: %s",
                pr_number,
                exc,
            )
            unconfirmed_ids = set()
        for unconfirmed_id in unconfirmed_ids:
            if unconfirmed_id in existing_comment_ids:
                # Already in-scope for SDK verification, but still needs special handling
                # (confirmation replies / unresolve) as an unconfirmed-resolved thread.
                reevaluated_unconfirmed_comment_ids.add(unconfirmed_id)
                continue
            unconfirmed_comment = self._fetch_review_comment_by_id(pr_number, unconfirmed_id)
            if unconfirmed_comment is None:
                continue
            if unconfirmed_comment.is_suppressed:
                continue
            comment_context = self._build_comment_verification_context(unconfirmed_comment, diff_context)
            comments_for_sdk.append((unconfirmed_comment, comment_context))
            reevaluated_unconfirmed_comment_ids.add(unconfirmed_comment.id)

        state_dir: Path | None = None
        reply_formatter = ReplyFormatter()
        if comments_for_sdk:
            tier_results_by_comment_id: dict[int, TierResult] = {}
            try:
                is_outdated_by_id = self._fetch_outdated_by_comment_id(pr_number)
            except Exception as exc:
                logger.warning(
                    "Failed to fetch thread outdated status for PR #%d: %s — is_outdated will be None",
                    pr_number,
                    exc,
                )
                is_outdated_by_id = {}
            try:
                latest_thread_comment_body_by_id = self._fetch_latest_thread_comment_body_by_comment_id(pr_number)
            except Exception as exc:
                logger.warning(
                    "Failed to fetch latest thread comment body for PR #%d: %s",
                    pr_number,
                    exc,
                )
                latest_thread_comment_body_by_id = {}
            sdk_verdicts = self._verify_comments_via_tiered_engine(
                comments_for_sdk,
                head_sha=head_sha,
                is_outdated_by_id=is_outdated_by_id,
                latest_thread_comment_body_by_id=latest_thread_comment_body_by_id,
                tier_results_out=tier_results_by_comment_id,
            )
            for comment, _context in comments_for_sdk:
                verdict = sdk_verdicts.get(comment.id, VerificationVerdict.COMMENT_UNRESOLVE)
                tier_result = tier_results_by_comment_id.get(comment.id)
                if tier_result is None and comment.id not in sdk_verdicts:
                    # Engine returned no result and no verdict was produced for
                    # this comment. Construct a fallback result and resolve by
                    # default since HEAD has changed.
                    logger.warning(
                        "Comment %d on PR #%d: tier evaluation produced no result — "
                        "resolving by default with unconfirmed marker",
                        comment.id,
                        pr_number,
                    )
                    tier_result = TierResult(
                        verdict=ResolutionVerdict.RESOLVE,
                        confidence="low",
                        tier_name="engine_fallback",
                        explanation="SDK evaluation could not produce a verdict "
                        "— resolved by default due to HEAD change.",
                    )
                    verdict = VerificationVerdict.COMMENT_RESOLVE
                elif (
                    verdict == VerificationVerdict.COMMENT_RESOLVE
                    and tier_result is not None
                    and tier_result.verdict == ResolutionVerdict.TENTATIVE
                ):
                    # Resolve-by-default outcomes should bypass tentative lifecycle
                    # persistence/replies. Keep an explicit engine_fallback marker
                    # so the thread can be re-evaluated later.
                    tier_result = TierResult(
                        verdict=ResolutionVerdict.RESOLVE,
                        confidence=tier_result.confidence,
                        tier_name="engine_fallback",
                        explanation=tier_result.explanation,
                    )
                if tier_result is not None:
                    if state_dir is None:
                        state_dir = self._resolution_state_dir()
                    thread_id = str(comment.id)
                    if tier_result.verdict == ResolutionVerdict.TENTATIVE:
                        state = load_resolution_state(thread_id, state_dir)
                        if state is not None and state.verdict == ResolutionVerdict.ABANDONED:
                            # Thread was previously abandoned; do not re-enter the lifecycle.
                            # Retry posting the abandoned reply if it was not posted previously.
                            if comment.id not in abandoned_reply_parent_comment_ids:
                                self._reply_to_review_comment(
                                    pr_number,
                                    comment.id,
                                    body=reply_formatter.format_abandoned_reply(),
                                )
                        else:
                            is_new_state = state is None
                            if state is None:
                                state = ThreadResolutionState(
                                    thread_id=thread_id,
                                    verdict=ResolutionVerdict.TENTATIVE,
                                    tier_name=tier_result.tier_name,
                                    confidence=tier_result.confidence,
                                )
                                save_resolution_state(state, state_dir)
                            else:
                                state.verdict = ResolutionVerdict.TENTATIVE
                                state.tier_name = tier_result.tier_name
                                state.confidence = tier_result.confidence
                                state = increment_iteration(state, state_dir)
                            if is_tentative_expired(state):
                                mark_abandoned(thread_id, state_dir)
                                if comment.id not in abandoned_reply_parent_comment_ids:
                                    self._reply_to_review_comment(
                                        pr_number,
                                        comment.id,
                                        body=reply_formatter.format_abandoned_reply(),
                                    )
                            elif is_new_state and not self._has_existing_addressed_reply(
                                pr_number, comment.id, addressed_reply_parent_comment_ids
                            ):
                                self._reply_to_review_comment(
                                    pr_number,
                                    comment.id,
                                    body=reply_formatter.build_full_reply(
                                        tier_result,
                                        model_id=self._model_id_for_tier_result(tier_result),
                                    ),
                                )
                    else:
                        clear_resolution_state(thread_id, state_dir)
                if verdict == VerificationVerdict.COMMENT_RESOLVE:
                    resolved_ids.append(comment.id)
                    has_existing_addressed_reply = self._has_existing_addressed_reply(
                        pr_number, comment.id, addressed_reply_parent_comment_ids
                    )
                    post_confirmation_reply = (
                        comment.id in reevaluated_unconfirmed_comment_ids
                        and tier_result is not None
                        and "fallback" not in (tier_result.tier_name or "")
                    )
                    if post_confirmation_reply or not has_existing_addressed_reply:
                        if tier_result is not None and "fallback" in (tier_result.tier_name or ""):
                            reply_body = reply_formatter.format_unconfirmed_commit_change_reply(
                                tier_result,
                                model_id=self._model_id_for_tier_result(tier_result),
                            )
                        elif post_confirmation_reply and tier_result is not None:
                            reply_body = reply_formatter.build_full_reply(
                                tier_result,
                                model_id=self._model_id_for_tier_result(tier_result),
                            )
                        else:
                            reply_body = _ADDRESSED_REPLY_BODY
                        self._reply_to_review_comment(pr_number, comment.id, body=reply_body)
                    resolutions.append(CommentResolution(comment_id=comment.id, verdict=verdict))
                else:
                    if (
                        verdict == VerificationVerdict.COMMENT_UNRESOLVE
                        and tier_result is not None
                        and tier_result.verdict == ResolutionVerdict.UNRESOLVE
                        and comment.id not in unresolve_reply_parent_comment_ids
                    ):
                        self._reply_to_review_comment(
                            pr_number,
                            comment.id,
                            body=reply_formatter.build_full_reply(
                                tier_result,
                                model_id=self._model_id_for_tier_result(tier_result),
                            ),
                        )
                    if (
                        verdict == VerificationVerdict.COMMENT_UNRESOLVE
                        and comment.id in reevaluated_unconfirmed_comment_ids
                    ):
                        unconfirmed_unresolve_ids.append(comment.id)
                    resolutions.append(CommentResolution(comment_id=comment.id, verdict=verdict))

        # Unresolve threads that were previously resolved with the unconfirmed marker
        # but are now vetoed by the SDK on re-evaluation
        if unconfirmed_unresolve_ids:
            unresolve_result = _unresolve_review_threads(
                pr_number,
                repo,
                comment_ids=sorted(unconfirmed_unresolve_ids),
            )
            if not bool(unresolve_result.get("verified", False)):
                errors.append("thread_unresolve_unverified")
            threads_failed = int(unresolve_result.get("threadsFailed", 0) or 0)
            if threads_failed > 0:
                errors.append(f"thread_unresolve_failed:{threads_failed}")

        # Resolve threads only for comments that were verified as addressed
        if resolved_ids:
            resolve_result = _resolve_review_threads(pr_number, repo, comment_ids=sorted(resolved_ids))
            details_by_comment_id: dict[int, dict[str, Any]] = {
                int(detail["commentId"]): detail
                for detail in resolve_result.get("details", [])
                if detail.get("commentId") is not None
            }
            updated_resolutions: list[CommentResolution] = []
            for resolution in resolutions:
                detail = details_by_comment_id.get(resolution.comment_id)
                thread_id = (
                    str(detail.get("threadId"))
                    if detail is not None and detail.get("threadId") is not None
                    else resolution.thread_id
                )
                error = resolution.error
                if resolution.verdict == VerificationVerdict.COMMENT_RESOLVE:
                    if detail is None:
                        error = "thread_resolution_missing"
                    else:
                        status = str(detail.get("status", ""))
                        if status not in {"resolved", "already_resolved"}:
                            error = str(detail.get("error") or f"thread_{status or 'unknown'}")
                updated_resolutions.append(
                    CommentResolution(
                        comment_id=resolution.comment_id,
                        thread_id=thread_id,
                        verdict=resolution.verdict,
                        error=error,
                    )
                )
            resolutions = updated_resolutions
            if not bool(resolve_result.get("verified", False)):
                errors.append("thread_resolution_unverified")
            threads_failed = int(resolve_result.get("threadsFailed", 0) or 0)
            if threads_failed > 0:
                errors.append(f"thread_resolution_failed:{threads_failed}")

        errors.extend(
            f"comment_{resolution.comment_id}:{resolution.error}" for resolution in resolutions if resolution.error
        )
        resolved_count = sum(
            1
            for resolution in resolutions
            if resolution.verdict == VerificationVerdict.COMMENT_RESOLVE and not resolution.error
        )
        unresolved_count = sum(
            1
            for resolution in resolutions
            if resolution.verdict != VerificationVerdict.COMMENT_RESOLVE or bool(resolution.error)
        )
        reason = "verified" if not errors else "verified_with_resolution_errors"

        result = FinalizationResult(
            skipped=False,
            reason=reason,
            resolved_count=resolved_count,
            unresolved_count=unresolved_count,
            resolutions=tuple(resolutions),
            errors=tuple(errors),
        )
        logger.info(
            "Finalization complete for PR #%d review %d: %d resolved, %d unresolved",
            pr_number,
            review_id,
            result.resolved_count,
            result.unresolved_count,
        )
        return result

    def _build_verification_context_diff(self, review_commit_sha: str, head_sha: str) -> str:
        """Fetch the diff between the review commit and HEAD for verification context.

        Returns the diff as a string, truncated to a 4000-token budget
        (approx 16000 chars using 4 chars/token heuristic).
        """
        max_chars = 16000
        try:
            result = run_safe(
                ["git", "diff", f"{review_commit_sha}..{head_sha}"],
                capture_output=True,
                text=True,
                shell=False,
            )
            diff = result.stdout if result.returncode == 0 else ""
        except Exception as exc:
            logger.warning("Failed to get diff for verification context: %s", exc)
            diff = ""

        if len(diff) > max_chars:
            diff = diff[:max_chars]
        return diff

    def _build_comment_verification_context(self, comment: ReviewCommentInfo, full_diff: str) -> str:
        """Build verification context for a specific comment.

        For line-anchored comments, extracts relevant portion of the diff.
        Falls back to diff_hunk when the file section cannot be found in the diff
        (e.g. no changes for that file, rename/copy, or path mismatch).
        For PR-level comments (no path), uses the full diff (already truncated).
        """
        if comment.path:
            target_header = f"diff --git a/{comment.path} b/{comment.path}"
            # Extract the section of the diff for this file
            lines = full_diff.split("\n")
            file_diff_lines: list[str] = []
            in_file = False
            for line in lines:
                if line == target_header:
                    in_file = True
                    file_diff_lines = [line]
                elif line.startswith("diff --git") and in_file:
                    break
                elif in_file:
                    file_diff_lines.append(line)
            if file_diff_lines:
                file_diff = "\n".join(file_diff_lines)
                if len(file_diff) > 4000:
                    return file_diff[:4000]
                return file_diff
            # File section not found — fall back to the original diff_hunk so the SDK
            # sees scoped context instead of unrelated changes from other files.
            # If no hunk is available, return empty context so verification defaults
            # to COMMENT_UNRESOLVE via the existing fail-safe path.
            return comment.diff_hunk

        if full_diff:
            return full_diff

        return comment.diff_hunk

    def _build_comment_verification_prompt(self, comment_body: str, diff_context: str) -> str:
        return (
            "You are a code review verification assistant. Your task is to determine whether "
            "a review comment has been addressed by the code changes in the diff.\n\n"
            "## Review Comment\n"
            f"{comment_body}\n\n"
            "## Diff (changes made since the review)\n"
            f"```diff\n{diff_context}\n```\n\n"
            "## Instructions\n"
            "Respond with EXACTLY one of these two values (nothing else):\n"
            "- COMMENT_RESOLVE — if the diff addresses the review comment\n"
            "- COMMENT_UNRESOLVE — if the diff does NOT address the review comment\n"
        )

    def _verify_comments_via_tiered_engine(
        self,
        comments: list[tuple[ReviewCommentInfo, str]],
        *,
        head_sha: str,
        is_outdated_by_id: dict[int, bool | None] | None = None,
        latest_thread_comment_body_by_id: dict[int, str] | None = None,
        tier_results_out: dict[int, TierResult] | None = None,
    ) -> dict[int, VerificationVerdict]:
        """Verify comments through the tiered resolution engine."""

        from agentic_devtools.cli.ci.resolution.tiers.diff_heuristic import DiffHeuristicTier

        engine = TieredResolutionEngine(
            cast(
                list[EvaluationTier],
                [
                    OutdatedTier(),
                    AutomationMarkerTier(),
                    DiffHeuristicTier(),
                    SdkEvaluationTier(
                        sdk_caller=self._run_prompt_via_sdk,
                        fallback_caller=self._run_prompt_via_sdk_fallback,
                    ),
                ],
            )
        )

        verdicts: dict[int, VerificationVerdict] = {}
        for comment, diff_context in comments:
            # FR-003 guard: if the comment was placed on the current HEAD commit,
            # there are no newer changes to evaluate against — skip tier evaluation.
            if comment.commit_id and comment.commit_id == head_sha:
                verdicts[comment.id] = VerificationVerdict.COMMENT_UNRESOLVE
                continue
            latest_thread_comment_body = (
                latest_thread_comment_body_by_id.get(comment.id)
                if latest_thread_comment_body_by_id is not None
                else None
            )
            thread_comments = [
                GitHubThreadComment(
                    body=comment.body,
                    created_at="",
                    author_login=None,
                    database_id=comment.id,
                )
            ]
            if latest_thread_comment_body and latest_thread_comment_body != comment.body:
                thread_comments.append(
                    GitHubThreadComment(
                        body=latest_thread_comment_body,
                        created_at="",
                        author_login=None,
                        database_id=None,
                    )
                )
            thread = GitHubReviewThread(
                thread_id=str(comment.id),
                file_path=comment.path or None,
                start_line=comment.start_line or comment.line,
                end_line=comment.end_line or comment.line,
                is_outdated=is_outdated_by_id.get(comment.id) if is_outdated_by_id is not None else None,
                comments=thread_comments,
                originating_review_commit_oid=comment.commit_id,
            )
            context = GitHubResolutionContext(diff_text=diff_context, head_commit_oid=head_sha)
            result = engine.evaluate_thread(cast(ReviewThread, thread), cast(ResolutionContext, context))
            if tier_results_out is not None:
                tier_results_out[comment.id] = result
            if result.verdict == ResolutionVerdict.RESOLVE:
                verdicts[comment.id] = VerificationVerdict.COMMENT_RESOLVE
            elif result.verdict == ResolutionVerdict.UNRESOLVE:
                verdicts[comment.id] = VerificationVerdict.COMMENT_UNRESOLVE
            elif result.verdict == ResolutionVerdict.TENTATIVE:
                verdicts[comment.id] = VerificationVerdict.COMMENT_RESOLVE
            else:  # pragma: no cover - exhaustive guard for future enum extension
                raise ValueError(f"Unsupported resolution verdict: {result.verdict}")
            logger.debug(
                "Comment %d: tier verdict %s → verification %s (tier=%s)",
                comment.id,
                result.verdict.value,
                verdicts[comment.id].value,
                result.tier_name,
            )
        return verdicts

    def _verify_comments_via_sdk(  # pragma: no cover - optional runtime SDK integration
        self,
        comments: list[tuple[int, str, str]] | list[tuple[ReviewCommentInfo, str]],
        timeout_seconds: int = 60,
        *,
        head_sha: str | None = None,
    ) -> dict[int, VerificationVerdict]:
        """Verify multiple comments in one SDK session to reduce startup overhead."""
        if not comments:
            return {}

        normalized_comments: list[tuple[ReviewCommentInfo, str]] = []
        for item in comments:
            if isinstance(item[0], ReviewCommentInfo):
                comment, diff_context = item
                normalized_comments.append((comment, diff_context))
            else:
                comment_id, comment_body, diff_context = item
                normalized_comments.append(
                    (
                        ReviewCommentInfo(
                            id=comment_id,
                            path="",
                            body=comment_body,
                            html_url="",
                        ),
                        diff_context,
                    )
                )

        if head_sha:
            return self._verify_comments_via_tiered_engine(normalized_comments, head_sha=head_sha)

        token = os.environ.get("COPILOT_GITHUB_TOKEN", "").strip()
        if not token:
            logger.warning("COPILOT_GITHUB_TOKEN not set — defaulting to COMMENT_UNRESOLVE (fail-safe)")
            return {comment.id: VerificationVerdict.COMMENT_UNRESOLVE for comment, _diff_context in normalized_comments}

        try:
            from copilot import CopilotClient, SubprocessConfig
            from copilot.session import PermissionHandler
        except Exception as exc:
            logger.warning("Copilot SDK unavailable for comment verification: %s", exc)
            return {comment.id: VerificationVerdict.COMMENT_UNRESOLVE for comment, _diff_context in normalized_comments}

        model = os.environ.get("COPILOT_MODEL", "claude-opus-4.6")

        async def _run() -> dict[int, VerificationVerdict]:
            client = None
            session = None
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
                        raise
                    session = await client.create_session(
                        model=model,
                        on_permission_request=PermissionHandler.approve_all,
                        infinite_sessions={"enabled": False},
                    )

                current_content_parts: list[str] | None = None
                current_done: asyncio.Event | None = None

                def on_event(event: Any) -> None:
                    if current_content_parts is None or current_done is None:
                        return
                    event_type = getattr(getattr(event, "type", None), "value", "")
                    if event_type == "assistant.message":
                        current_content_parts.append(getattr(getattr(event, "data", None), "content", ""))
                    elif event_type in {"session.idle", "error", "session.error", "assistant.error"}:
                        current_done.set()

                session.on(on_event)

                verdicts: dict[int, VerificationVerdict] = {}
                for comment, diff_context in normalized_comments:
                    comment_id = comment.id
                    comment_body = comment.body
                    if not diff_context:
                        logger.warning("Empty diff context — defaulting to COMMENT_UNRESOLVE")
                        verdicts[comment_id] = VerificationVerdict.COMMENT_UNRESOLVE
                        continue

                    current_content_parts = []
                    current_done = asyncio.Event()
                    prompt = self._build_comment_verification_prompt(comment_body, diff_context)
                    await session.send(prompt)
                    try:
                        await asyncio.wait_for(current_done.wait(), timeout=timeout_seconds)
                    except asyncio.TimeoutError:
                        logger.warning(
                            "Copilot SDK comment verification timed out after %ds for comment %d",
                            timeout_seconds,
                            comment_id,
                        )
                        verdicts[comment_id] = VerificationVerdict.COMMENT_UNRESOLVE
                        continue

                    raw = (current_content_parts[-1] if current_content_parts else "").strip()
                    if "COMMENT_RESOLVE" in raw and "COMMENT_UNRESOLVE" not in raw:
                        verdicts[comment_id] = VerificationVerdict.COMMENT_RESOLVE
                    else:
                        verdicts[comment_id] = VerificationVerdict.COMMENT_UNRESOLVE
                return verdicts
            finally:
                if session is not None:
                    try:
                        await session.disconnect()
                    except Exception:
                        pass
                if client is not None:
                    try:
                        await client.stop()
                    except Exception:
                        pass

        total_timeout = timeout_seconds * len(normalized_comments)
        try:
            return asyncio.run(asyncio.wait_for(_run(), timeout=total_timeout))
        except asyncio.TimeoutError:
            logger.warning("Copilot SDK comment batch verification timed out after %ds", total_timeout)
            return {comment.id: VerificationVerdict.COMMENT_UNRESOLVE for comment, _diff_context in normalized_comments}
        except Exception as exc:
            logger.warning("Copilot SDK comment batch verification failed: %s", exc)
            return {comment.id: VerificationVerdict.COMMENT_UNRESOLVE for comment, _diff_context in normalized_comments}

    def _run_prompt_via_sdk_fallback(self, prompt: str, timeout_seconds: int = 60) -> str:
        """Run a single prompt via fallback model."""
        return self._run_prompt_via_sdk(
            prompt,
            timeout_seconds=timeout_seconds,
            model=os.environ.get("COPILOT_FALLBACK_MODEL", "claude-sonnet-4.6"),
        )

    def _run_prompt_via_sdk(
        self,
        prompt: str,
        timeout_seconds: int = 60,
        *,
        model: str | None = None,
    ) -> str:
        """Run a single prompt via Copilot SDK and return raw assistant output."""
        token = os.environ.get("COPILOT_GITHUB_TOKEN", "").strip()
        if not token:
            raise RuntimeError("COPILOT_GITHUB_TOKEN not set")

        try:
            from copilot import CopilotClient, SubprocessConfig
            from copilot.session import PermissionHandler
        except Exception as exc:
            raise RuntimeError(f"Copilot SDK unavailable: {exc}") from exc

        selected_model = model or os.environ.get("COPILOT_MODEL", "claude-opus-4.6")

        async def _run() -> str:  # pragma: no cover - optional runtime SDK integration
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
                        model=selected_model,
                        on_permission_request=PermissionHandler.approve_all,
                        infinite_sessions={"enabled": False},
                        github_token=token,
                    )
                except TypeError as exc:
                    if "unexpected keyword argument" not in str(exc) or "github_token" not in str(exc):
                        raise
                    session = await client.create_session(
                        model=selected_model,
                        on_permission_request=PermissionHandler.approve_all,
                        infinite_sessions={"enabled": False},
                    )

                from typing import Any as _Any

                def on_event(event: _Any) -> None:
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
                await asyncio.wait_for(done.wait(), timeout=timeout_seconds)

                if error_messages:
                    raise RuntimeError("; ".join(error_messages))

                raw = (content_parts[-1] if content_parts else "").strip()
                if not raw:
                    raise RuntimeError("empty SDK response")
                return raw
            finally:
                if session is not None:
                    try:
                        await session.disconnect()
                    except Exception:
                        pass
                if client is not None:
                    try:
                        await client.stop()
                    except Exception:
                        pass

        try:
            return asyncio.run(asyncio.wait_for(_run(), timeout=timeout_seconds))
        except asyncio.TimeoutError as exc:  # pragma: no cover
            raise RuntimeError(f"Copilot SDK prompt timed out after {timeout_seconds}s") from exc
        except RuntimeError:
            raise
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(f"Copilot SDK prompt failed: {exc}") from exc

    def _verify_comment_via_sdk(
        self,
        comment_body: str,
        diff_context: str,
        timeout_seconds: int = 60,
    ) -> VerificationVerdict:
        """Verify whether a review comment has been addressed by the diff via Copilot SDK.

        Returns COMMENT_RESOLVE if addressed, COMMENT_UNRESOLVE otherwise.
        Defaults to COMMENT_UNRESOLVE on any error (fail-safe).
        """
        if not diff_context:
            logger.warning("Empty diff context — defaulting to COMMENT_UNRESOLVE")
            return VerificationVerdict.COMMENT_UNRESOLVE

        prompt = self._build_comment_verification_prompt(comment_body, diff_context)
        try:
            raw = self._run_prompt_via_sdk(prompt, timeout_seconds=timeout_seconds)
        except RuntimeError as exc:
            logger.warning("Copilot SDK comment verification failed: %s", exc)
            return VerificationVerdict.COMMENT_UNRESOLVE

        if "COMMENT_RESOLVE" in raw and "COMMENT_UNRESOLVE" not in raw:
            return VerificationVerdict.COMMENT_RESOLVE
        return VerificationVerdict.COMMENT_UNRESOLVE

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

        # 3. Re-request Copilot review with built-in verification.
        #    Force-push is the primary auto-trigger mechanism; this explicit request
        #    serves as a fallback safety net.  _request_copilot_review already verifies
        #    via both requested-reviewers polling and the reviews fallback (covering the
        #    case where Copilot started reviewing before our verification poll runs).
        repo = self._resolve_repo()
        result = _request_copilot_review(pr_number, repo)

        # 3b. Re-request once if the initial request was not verified.
        #     Unlike a manual requested_reviewers check, this reuses the richer
        #     verification logic in _request_copilot_review itself.
        if not result.get("verified"):
            logger.warning(
                "Copilot review request not verified for PR #%d after force-push "
                "(requested=%s). Re-requesting explicitly.",
                pr_number,
                result.get("requested"),
            )
            _request_copilot_review(pr_number, repo)
