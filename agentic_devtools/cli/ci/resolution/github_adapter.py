"""GitHub-specific adapter for the tiered resolution system.

Converts raw GraphQL response nodes into ReviewThread protocol instances
for use by the tiered resolution engine.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GitHubThreadComment:
    """A GitHub review thread comment."""

    body: str
    created_at: str
    author_login: str | None
    database_id: int | None = None


@dataclass(frozen=True)
class GitHubReviewThread:
    """A GitHub review thread with all metadata for tiered evaluation."""

    thread_id: str
    file_path: str | None
    start_line: int | None
    end_line: int | None
    is_outdated: bool | None
    comments: list[GitHubThreadComment] = field(default_factory=list)
    originating_review_commit_oid: str = ""


@dataclass(frozen=True)
class GitHubResolutionContext:
    """GitHub-specific resolution context."""

    diff_text: str
    head_commit_oid: str


class GitHubThreadAdapter:
    """Converts raw GraphQL thread data into ReviewThread protocol instances."""

    def adapt_thread(self, node: dict[str, Any]) -> GitHubReviewThread:
        """Convert a single GraphQL thread node to a GitHubReviewThread.

        Args:
            node: Raw GraphQL thread node from the reviewThreads query.

        Returns:
            A GitHubReviewThread instance.
        """
        comments: list[GitHubThreadComment] = []
        commit_oid = ""

        for comment_node in node.get("comments", {}).get("nodes", []):
            comment = GitHubThreadComment(
                body=comment_node.get("body", ""),
                created_at=comment_node.get("createdAt", ""),
                author_login=(comment_node.get("author") or {}).get("login"),
                database_id=comment_node.get("databaseId"),
            )
            comments.append(comment)
            # Use the first comment's commit OID as the originating review commit
            if not commit_oid:
                commit_node = comment_node.get("commit") or {}
                commit_oid = commit_node.get("oid", "")

        return GitHubReviewThread(
            thread_id=node.get("id", ""),
            file_path=node.get("path"),
            start_line=node.get("startLine") or node.get("line"),
            end_line=node.get("line"),
            is_outdated=node.get("isOutdated"),
            comments=comments,
            originating_review_commit_oid=commit_oid,
        )

    def adapt_threads(self, nodes: list[dict[str, Any]]) -> list[GitHubReviewThread]:
        """Convert multiple GraphQL thread nodes.

        Args:
            nodes: List of raw GraphQL thread nodes.

        Returns:
            List of GitHubReviewThread instances.
        """
        return [self.adapt_thread(node) for node in nodes]
