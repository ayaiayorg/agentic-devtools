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

    def __init__(self, config: JiraConfig, project_key: str | None = None, issue_type: str = "Task") -> None:
        self._config = config
        self._project_key = project_key or ""
        self._issue_type = issue_type

    def _require_project_key(self) -> str:
        """Return the configured project key, raising if unset.

        Only :meth:`create_issue` needs a project key; read/comment
        operations work without one.  This keeps adapter construction
        lazy — matching the factory's stated design.
        """
        if not self._project_key:
            raise ValueError(
                "JiraAdapter.create_issue requires a Jira project_key, but none was "
                "configured. Set platform.jira.project_key in configuration or pass "
                "project_key when constructing JiraAdapter."
            )
        return self._project_key

    def create_issue(self, title: str, description: str, labels: list[str] | None = None) -> IssueResult:
        """Create a Jira issue and return a shared :class:`IssueResult`."""
        project_key = self._require_project_key()
        result = jira_create_issue(
            config=self._config,
            project_key=project_key,
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
        raw_description = fields.get("description")
        # Jira Cloud may return ADF (dict) instead of plain text; coerce to str.
        if raw_description is None:
            description = ""
        elif isinstance(raw_description, str):
            description = raw_description
        else:
            description = str(raw_description)
        raw_labels = fields.get("labels")
        labels = [label for label in raw_labels if isinstance(label, str)] if isinstance(raw_labels, list) else []
        status = fields.get("status", {}).get("name", "") if isinstance(fields.get("status"), dict) else ""
        url = f"{self._config.base_url}/browse/{issue_id}"

        comment_field = fields.get("comment")
        raw_comments = comment_field.get("comments") if isinstance(comment_field, dict) else None
        if not isinstance(raw_comments, list):
            raw_comments = []
        comments: list[Comment] = []
        for c in raw_comments:
            if not isinstance(c, dict):
                continue
            raw_body = c.get("body", "")
            if not isinstance(raw_body, str):
                raw_body = "" if raw_body is None else str(raw_body)
            raw_created = c.get("created", "")
            if not isinstance(raw_created, str):
                raw_created = "" if raw_created is None else str(raw_created)
            comments.append(
                Comment(
                    comment_id=str(c.get("id", "")),
                    body=raw_body,
                    created_at=raw_created,
                )
            )

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
