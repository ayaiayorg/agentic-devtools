"""IssueContextRetriever — aggregates project context for AI agent invocations."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from agentic_devtools.tools.git import get_recent_changes
from agentic_devtools.tools.jira import JiraConfig, fetch_issue_context

from .models import AgentContext

logger = logging.getLogger(__name__)


class IssueContextRetriever:
    """Aggregates issue details, file paths, Git changes, coverage, and docs.

    Args:
        jira_config: Configuration for Jira API access.
        repo_path: Project root directory path.
        coverage_path: Optional explicit path to ``coverage.json``.
            Defaults to ``{repo_path}/coverage.json``.
    """

    def __init__(
        self,
        jira_config: JiraConfig,
        repo_path: str,
        coverage_path: str | None = None,
    ) -> None:
        repo = Path(repo_path)
        if not repo.is_dir():
            raise ValueError("repo_path must be a valid directory")
        self._jira_config = jira_config
        self._repo_path = repo
        # Resolve relative coverage_path against repo_path for consistency
        if coverage_path:
            coverage = Path(coverage_path)
            self._coverage_path = coverage if coverage.is_absolute() else repo / coverage
        else:
            self._coverage_path = repo / "coverage.json"

    async def retrieve(
        self,
        issue_key: str,
        affected_paths: list[str] | None = None,
        num_recent_commits: int = 10,
    ) -> AgentContext:
        """Retrieve and aggregate all context subsystems into an :class:`AgentContext`.

        Each subsystem call is wrapped in a try/except so that failures are
        non-fatal — errors are recorded in :pyattr:`AgentContext.errors` and
        retrieval continues.
        """
        ctx = AgentContext(issue_key=issue_key)

        # --- Jira issue details ---
        try:
            result = await asyncio.to_thread(
                fetch_issue_context,
                self._jira_config,
                issue_key,
            )
            ctx.issue_details = result.get("issue")
            ctx.parent_issue = result.get("parent_issue")
            ctx.epic_issue = result.get("epic_issue")
            ctx.remote_links = result.get("remote_links", [])
        except Exception as exc:
            msg = f"Failed to fetch Jira issue {issue_key}: {exc}"
            logger.warning(msg)
            ctx.errors.append(msg)

        # --- Validate affected paths ---
        if affected_paths is not None:
            for p in affected_paths:
                validated = self._validate_path(p)
                if validated is not None:
                    ctx.relevant_files.append(p)
                else:
                    msg = f"Affected path rejected or does not exist: {p}"
                    logger.warning(msg)
                    ctx.errors.append(msg)

        # --- Recent Git changes ---
        try:
            changes = await asyncio.to_thread(get_recent_changes, num_recent_commits)
            ctx.recent_changes = changes.get("commits", [])
        except Exception as exc:
            msg = f"Failed to fetch recent Git changes: {exc}"
            logger.warning(msg)
            ctx.errors.append(msg)

        # --- Test coverage ---
        try:
            ctx.test_coverage = self._parse_coverage(ctx.relevant_files)
        except Exception as exc:
            msg = f"Failed to parse coverage data: {exc}"
            logger.warning(msg)
            ctx.errors.append(msg)

        # --- Documentation ---
        try:
            ctx.documentation = self._find_documentation(affected_paths)
        except Exception as exc:
            msg = f"Failed to find documentation: {exc}"
            logger.warning(msg)
            ctx.errors.append(msg)

        return ctx

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _validate_path(self, p: str) -> Path | None:
        """Validate that *p* is a safe relative path within the repo.

        Rejects absolute paths, ``..`` traversal, and paths that resolve
        outside ``self._repo_path``.  Returns the resolved :class:`Path`
        if valid and existing, otherwise ``None``.
        """
        pp = Path(p)
        if pp.is_absolute():
            return None
        # Reject any component that is ".."
        if ".." in pp.parts:
            return None
        full = (self._repo_path / pp).resolve()
        if not self._is_within_repo(full):
            return None
        if not full.exists():
            return None
        return full

    def _is_within_repo(self, resolved: Path) -> bool:
        """Return *True* if *resolved* is inside ``self._repo_path``."""
        try:
            resolved.relative_to(self._repo_path.resolve())
            return True
        except ValueError:
            return False

    def _parse_coverage(self, affected_paths: list[str]) -> dict[str, Any]:
        """Parse ``coverage.json`` and extract data for *affected_paths*."""
        if not self._coverage_path.exists():
            raise FileNotFoundError(f"Coverage file not found: {self._coverage_path}")

        raw = self._coverage_path.read_text(encoding="utf-8")
        data = json.loads(raw)
        files_section = data.get("files", {})

        result: dict[str, Any] = {}
        for path in affected_paths:
            entry = files_section.get(path)
            if entry is not None:
                result[path] = entry
        return result

    def _find_documentation(self, affected_paths: list[str] | None) -> list[dict[str, str]]:
        """Scan for documentation files related to *affected_paths*."""
        if not affected_paths:
            return []

        max_lines = 200
        found: dict[str, str] = {}

        # Always include root README.md
        root_readme = self._repo_path / "README.md"
        if root_readme.exists():
            found[str(root_readme.relative_to(self._repo_path))] = self._read_lines(root_readme, max_lines)

        for p in affected_paths:
            pp = Path(p)
            stem = pp.stem  # e.g. "jira" from "agentic_devtools/tools/jira.py"
            parent_parts = pp.parent.parts  # e.g. ("agentic_devtools", "tools")

            # Look for docs matching the path stem
            candidates = [
                self._repo_path / "docs" / "/".join(parent_parts[1:]) / f"{stem}.md" if len(parent_parts) > 1 else None,
                self._repo_path / "docs" / f"{stem}.md",
            ]
            # Also look for a parent module doc
            if len(parent_parts) > 1:
                candidates.append(self._repo_path / "docs" / f"{parent_parts[-1]}.md")
            # Check for README.md in the same directory
            candidates.append(self._repo_path / pp.parent / "README.md")

            for candidate in candidates:
                if candidate is None:
                    continue
                # Ensure candidate resolves within the repo to prevent escapes
                resolved = candidate.resolve()
                if not self._is_within_repo(resolved):
                    continue
                try:
                    rel = str(candidate.relative_to(self._repo_path))
                except ValueError:
                    continue
                if candidate.exists() and rel not in found:
                    try:
                        found[rel] = self._read_lines(candidate, max_lines)
                    except Exception as exc:
                        msg = f"Failed to read documentation file {candidate}: {exc}"
                        logger.warning(msg)
                        raise

        return [{"path": path, "content": content} for path, content in found.items()]

    @staticmethod
    def _read_lines(path: Path, max_lines: int) -> str:
        """Read up to *max_lines* from *path*."""
        lines: list[str] = []
        with path.open(encoding="utf-8") as fh:
            for i, line in enumerate(fh):
                if i >= max_lines:
                    break
                lines.append(line)
        return "".join(lines)
