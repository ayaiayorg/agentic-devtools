"""Exclusion context for passing resolved comment IDs between pipeline actions."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ExclusionContext:
    """Carry resolved review comment IDs from the apply-suggestions step to repair dispatch.

    Attributes:
        resolved_comment_ids: Set of REST API ``databaseId`` values from
            ``PullRequestReviewComment`` nodes whose suggestions were
            successfully applied. These are excluded from repair dispatch
            context to prevent double-handling.
    """

    resolved_comment_ids: set[int] = field(default_factory=set)

    def merge(self, other: ExclusionContext) -> ExclusionContext:
        """Merge another ExclusionContext into this one, returning a new instance."""
        return ExclusionContext(
            resolved_comment_ids=self.resolved_comment_ids | other.resolved_comment_ids,
        )
