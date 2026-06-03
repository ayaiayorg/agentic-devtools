"""PR label toggle provider protocol.

Defines the abstract interface for toggling a label on pull requests.
Platform-specific implementations (GitHub, Azure DevOps) implement this protocol.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class PrInfo:
    """Minimal PR info returned by the provider."""

    number: int
    is_open: bool


class PrLabelToggleProvider(ABC):
    """Abstract provider for PR label toggle operations."""

    @abstractmethod
    def get_newest_open_pr(self) -> PrInfo | None:
        """Return the newest open PR, or None if there are no open PRs."""

    @abstractmethod
    def is_pr_open(self, pr_number: int) -> bool:
        """Check whether a PR is still open."""

    @abstractmethod
    def has_label(self, pr_number: int, label: str) -> bool | None:
        """Check if a PR has the given label.

        Returns:
            True if label is present, False if absent, None on parse failure.
        """

    @abstractmethod
    def add_label(self, pr_number: int, label: str) -> None:
        """Add a label to a PR."""

    @abstractmethod
    def remove_label(self, pr_number: int, label: str) -> None:
        """Remove a label from a PR."""
