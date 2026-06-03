"""GitHub implementation of the PR label toggle provider."""

from __future__ import annotations

import json

from ..subprocess_utils import run_safe
from . import PrInfo, PrLabelToggleProvider


class GitHubPrLabelToggleProvider(PrLabelToggleProvider):
    """Toggle PR labels on GitHub repos via the ``gh`` CLI."""

    def __init__(self, repo: str) -> None:
        self._repo = repo

    def _safe_json(self, raw: str) -> object | None:
        """Parse JSON from gh output, skipping non-JSON lines."""
        for line in raw.splitlines():
            trimmed = line.strip()
            if trimmed.startswith("[") or trimmed.startswith("{"):
                try:
                    return json.loads(trimmed)
                except (json.JSONDecodeError, ValueError):
                    continue
        return None

    def get_newest_open_pr(self) -> PrInfo | None:
        """Return the newest open PR via ``gh pr list``."""
        result = run_safe(
            ["gh", "pr", "list", "--repo", self._repo, "--state", "open", "--limit", "1", "--json", "number"],
            capture_output=True,
            text=True,
            shell=False,
        )
        if result.returncode != 0:
            return None
        data = self._safe_json(result.stdout)
        if not data or not isinstance(data, list) or len(data) == 0:
            return None
        return PrInfo(number=data[0]["number"], is_open=True)

    def is_pr_open(self, pr_number: int) -> bool:
        """Check PR state via ``gh pr view``."""
        result = run_safe(
            ["gh", "pr", "view", str(pr_number), "--repo", self._repo, "--json", "state"],
            capture_output=True,
            text=True,
            shell=False,
        )
        if result.returncode != 0:
            return False
        data = self._safe_json(result.stdout)
        if not data or not isinstance(data, dict):
            return False
        return data.get("state") == "OPEN"

    def has_label(self, pr_number: int, label: str) -> bool | None:
        """Check if label exists on PR via ``gh pr view``."""
        result = run_safe(
            ["gh", "pr", "view", str(pr_number), "--repo", self._repo, "--json", "labels"],
            capture_output=True,
            text=True,
            shell=False,
        )
        if result.returncode != 0:
            return None
        data = self._safe_json(result.stdout)
        if not data or not isinstance(data, dict):
            return None
        labels = data.get("labels", [])
        return any(lbl.get("name") == label for lbl in labels)

    def add_label(self, pr_number: int, label: str) -> None:
        """Add label via ``gh pr edit``."""
        run_safe(
            ["gh", "pr", "edit", str(pr_number), "--repo", self._repo, "--add-label", label],
            capture_output=True,
            text=True,
            shell=False,
        )

    def remove_label(self, pr_number: int, label: str) -> None:
        """Remove label via ``gh pr edit``."""
        run_safe(
            ["gh", "pr", "edit", str(pr_number), "--repo", self._repo, "--remove-label", label],
            capture_output=True,
            text=True,
            shell=False,
        )
