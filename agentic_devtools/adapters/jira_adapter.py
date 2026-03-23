"""Jira issue adapter wrapping ``agentic_devtools.tools.jira`` functions.

Maps Jira-specific API results to the shared adapter TypedDicts defined
in :mod:`agentic_devtools.adapters.base`.
"""

from __future__ import annotations

import logging

from agentic_devtools.adapters.base import (
    Comment,
    CommentResult,
    IssueAdapter,
    IssueDetail,
    IssueFilters,
    IssueResult,
    IssueSummary,
)
from agentic_devtools.tools.jira import JiraConfig
from agentic_devtools.tools.jira import add_comment as jira_add_comment
from agentic_devtools.tools.jira import create_issue as jira_create_issue
from agentic_devtools.tools.jira import fetch_issue_context as jira_fetch_issue_context

logger = logging.getLogger(__name__)


class JiraAdapter(IssueAdapter):
    """Issue adapter backed by Jira REST API via :mod:`agentic_devtools.tools.jira`."""

    def __init__(self, config: JiraConfig, project_key: str, issue_type: str = "Task") -> None:
        if not project_key:
            raise ValueError("project_key is required for JiraAdapter")
        self._config = config
        self._project_key = project_key
        self._issue_type = issue_type

    def create_issue(self, title: str, description: str, labels: list[str] | None = None) -> IssueResult:
        """Create a Jira issue and return a shared :class:`IssueResult`."""
        result = jira_create_issue(
            config=self._config,
            project_key=self._project_key,
            summary=title,
            issue_type=self._issue_type,
            description=description,
            labels=labels or [],
        )
        return IssueResult(issue_id=result["issue_key"], url=result["url"])

    def get_issue(self, issue_id: str) -> IssueDetail:
        """Fetch a Jira issue and return a shared :class:`IssueDetail`."""
        ctx = jira_fetch_issue_context(config=self._config, issue_key=issue_id)
        issue = ctx["issue"]
        fields = issue.get("fields", {})

        title = fields.get("summary", "")
        description = fields.get("description") or ""
        labels = fields.get("labels", [])
        status = fields.get("status", {}).get("name", "") if isinstance(fields.get("status"), dict) else ""
        url = f"{self._config.base_url}/browse/{issue_id}"

        raw_comments = fields.get("comment", {}).get("comments", []) if isinstance(fields.get("comment"), dict) else []
        comments: list[Comment] = [
            Comment(
                comment_id=str(c.get("id", "")),
                body=c.get("body", ""),
                created_at=c.get("created", ""),
            )
            for c in raw_comments
        ]

        return IssueDetail(
            issue_id=issue_id,
            title=title,
            description=description,
            status=status,
            labels=labels,
            url=url,
            comments=comments,
        )

    def add_comment(self, issue_id: str, comment: str) -> CommentResult:
        """Add a comment to a Jira issue."""
        result = jira_add_comment(config=self._config, issue_key=issue_id, comment=comment)
        return CommentResult(comment_id=result["comment_id"])

    def list_issues(self, filters: IssueFilters | None = None) -> list[IssueSummary]:
        """Not yet implemented for Jira."""
        raise NotImplementedError("JiraAdapter.list_issues is not yet implemented. Full Jira search is a future issue.")
