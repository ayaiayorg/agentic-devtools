"""GitHub Issues adapter using the ``gh`` CLI via subprocess.

Wraps ``gh issue`` commands and parses their JSON output into the shared
adapter TypedDicts defined in :mod:`agentic_devtools.adapters.base`.
"""

from __future__ import annotations

import json
import logging
import subprocess
from collections.abc import Callable

from agentic_devtools.adapters.base import (
    Comment,
    CommentResult,
    IssueAdapter,
    IssueDetail,
    IssueFilters,
    IssueResult,
    IssueSummary,
)
from agentic_devtools.cli.subprocess_utils import run_safe

logger = logging.getLogger(__name__)


class GitHubIssuesAdapter(IssueAdapter):
    """Issue adapter backed by the ``gh`` CLI for GitHub Issues."""

    def __init__(
        self,
        repo: str,
        run_command: Callable[..., subprocess.CompletedProcess] | None = None,
    ) -> None:
        self._repo = repo
        self._run: Callable[..., subprocess.CompletedProcess] = run_command or run_safe

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _exec(self, args: list[str]) -> subprocess.CompletedProcess:
        """Run a ``gh`` command and raise on failure."""
        result = self._run(args, capture_output=True, text=True, shell=False)
        if result.returncode != 0:
            raise RuntimeError(f"gh command failed: {result.stderr}")
        return result

    def _parse_json(self, stdout: str) -> object:
        """Parse JSON from *stdout*, raising on failure."""
        try:
            return json.loads(stdout)
        except (json.JSONDecodeError, TypeError) as exc:
            raise RuntimeError(f"Failed to parse gh output: {exc}") from exc

    # ------------------------------------------------------------------
    # IssueAdapter interface
    # ------------------------------------------------------------------

    def create_issue(self, title: str, description: str, labels: list[str] | None = None) -> IssueResult:
        """Create a GitHub issue via ``gh issue create``."""
        args = ["gh", "issue", "create", "--repo", self._repo, "--title", title, "--body", description]
        for label in labels or []:
            args += ["--label", label]
        result = self._exec(args)
        url = result.stdout.strip()
        issue_id = url.rstrip("/").rsplit("/", 1)[-1] if url else ""
        return IssueResult(issue_id=issue_id, url=url)

    def get_issue(self, issue_id: str) -> IssueDetail:
        """Fetch a GitHub issue via ``gh issue view``."""
        args = [
            "gh",
            "issue",
            "view",
            issue_id,
            "--repo",
            self._repo,
            "--json",
            "number,title,body,state,labels,url,comments",
        ]
        result = self._exec(args)
        data = self._parse_json(result.stdout)
        if not isinstance(data, dict):
            raise RuntimeError(f"Failed to parse gh output: expected dict, got {type(data).__name__}")

        raw_labels = data.get("labels") or []
        label_names = [lb["name"] if isinstance(lb, dict) else str(lb) for lb in raw_labels]

        raw_comments = data.get("comments") or []
        comments: list[Comment] = [
            Comment(
                comment_id=str(c.get("id", "")),
                body=c.get("body", ""),
                created_at=c.get("createdAt", ""),
            )
            for c in raw_comments
        ]

        return IssueDetail(
            issue_id=str(data.get("number", "")),
            title=data.get("title", ""),
            description=data.get("body", ""),
            status=data.get("state", ""),
            labels=label_names,
            url=data.get("url", ""),
            comments=comments,
        )

    def add_comment(self, issue_id: str, comment: str) -> CommentResult:
        """Add a comment via ``gh issue comment``."""
        args = ["gh", "issue", "comment", issue_id, "--repo", self._repo, "--body", comment]
        self._exec(args)
        return CommentResult(comment_id="")

    def list_issues(self, filters: IssueFilters | None = None) -> list[IssueSummary]:
        """List GitHub issues via ``gh issue list``."""
        args = ["gh", "issue", "list", "--repo", self._repo, "--json", "number,title,state,labels,url"]
        if filters:
            for label in filters.get("labels", []):
                args += ["--label", label]
            state = filters.get("state")
            if state:
                args += ["--state", state]
            assignee = filters.get("assignee")
            if assignee:
                args += ["--assignee", assignee]

        result = self._exec(args)
        items = self._parse_json(result.stdout)
        if not isinstance(items, list):
            raise RuntimeError(f"Failed to parse gh output: expected list, got {type(items).__name__}")

        summaries: list[IssueSummary] = []
        for item in items:
            raw_labels = item.get("labels") or []
            label_names = [lb["name"] if isinstance(lb, dict) else str(lb) for lb in raw_labels]
            summaries.append(
                IssueSummary(
                    issue_id=str(item.get("number", "")),
                    title=item.get("title", ""),
                    status=item.get("state", ""),
                    labels=label_names,
                    url=item.get("url", ""),
                )
            )
        return summaries
