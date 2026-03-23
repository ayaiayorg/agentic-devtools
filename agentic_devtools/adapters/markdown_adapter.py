"""Markdown file-based issue adapter.

Stores issues as individual markdown files with YAML frontmatter under
``.agdt/issues/`` in the repository root.  Provides a lightweight
alternative for users who do not use Jira or GitHub Issues.
"""

from __future__ import annotations

import datetime
import logging
import re
import shutil
from pathlib import Path

import yaml

from agentic_devtools.adapters.base import (
    Comment,
    CommentResult,
    IssueAdapter,
    IssueDetail,
    IssueFilters,
    IssueResult,
    IssueSummary,
)

logger = logging.getLogger(__name__)

_ID_PATTERN = re.compile(r"^\d{3}$")
_ARCHIVE_PATTERN = re.compile(r"^A_(\d{3})$")


def _coerce_str(value: object, default: str = "") -> str:
    """Coerce a YAML-loaded value to ``str``.

    Returns *default* when *value* is ``None``, otherwise ``str(value)``.
    Strings are returned as-is (no unnecessary conversion).
    """
    if value is None:
        return default
    return value if isinstance(value, str) else str(value)


def _is_frontmatter_delimiter(line: str) -> bool:
    """Return ``True`` when *line* is an unindented ``---`` delimiter."""
    return line.startswith("---") and line.rstrip("\r\n") == "---"


class MarkdownAdapter(IssueAdapter):
    """Issue adapter that reads/writes markdown files in ``.agdt/issues/``."""

    def __init__(self, repo_path: str) -> None:
        self._issues_dir = Path(repo_path) / ".agdt" / "issues"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _next_id(self) -> str:
        """Determine the next 3-digit zero-padded issue ID.

        If the current max ID is 999, archives all existing files first.
        """
        if not self._issues_dir.exists():
            return "001"

        existing = sorted(int(p.stem) for p in self._issues_dir.glob("*.md") if _ID_PATTERN.match(p.stem))
        if not existing:
            return "001"

        max_id = existing[-1]
        if max_id >= 999:
            self._archive()
            return "001"

        return f"{max_id + 1:03d}"

    def _archive(self) -> None:
        """Archive issue ``.md`` files whose stem is a 3-digit ID into a new archive folder.

        Non-issue markdown files (for example, ``readme.md``) are left in place.
        """
        existing_archives = sorted(
            int(m.group(1)) for d in self._issues_dir.iterdir() if d.is_dir() and (m := _ARCHIVE_PATTERN.match(d.name))
        )
        next_archive_num = (existing_archives[-1] + 1) if existing_archives else 0
        archive_dir = self._issues_dir / f"A_{next_archive_num:03d}"

        if archive_dir.exists():
            raise FileExistsError(f"Archive directory already exists: {archive_dir}")

        archive_dir.mkdir(parents=True)

        # Only archive files whose stem matches the 3-digit issue ID pattern,
        # so user-maintained files (e.g. readme.md) are not relocated.
        for md_file in self._issues_dir.glob("*.md"):
            if _ID_PATTERN.match(md_file.stem):
                shutil.move(str(md_file), str(archive_dir / md_file.name))

    @staticmethod
    def _write_issue(path: Path, frontmatter: dict, description: str) -> None:
        """Write an issue file with YAML frontmatter and markdown body."""
        yaml_str = yaml.safe_dump(frontmatter, default_flow_style=False, sort_keys=False)
        path.write_text(f"---\n{yaml_str}---\n{description}\n", encoding="utf-8")

    @staticmethod
    def _read_issue(path: Path, issue_id: str) -> tuple[dict, str]:
        """Read and parse an issue file, returning (frontmatter, description).

        Uses line-based delimiter detection so that ``---`` inside YAML
        scalar values (e.g. a title containing ``---``) does not break
        the parser.
        """
        content = path.read_text(encoding="utf-8")
        lines = content.splitlines(keepends=True)
        if not lines or not _is_frontmatter_delimiter(lines[0]):
            raise ValueError(f"Invalid frontmatter in issue {issue_id}")

        # Collect YAML frontmatter lines until the closing '---' delimiter
        # line.  Only an *unindented* ``---`` (no leading whitespace) is
        # treated as the closing delimiter so that ``---`` inside indented
        # YAML block scalars is not misinterpreted.
        fm_lines: list[str] = []
        i = 1
        while i < len(lines) and not _is_frontmatter_delimiter(lines[i]):
            fm_lines.append(lines[i])
            i += 1

        if i >= len(lines):
            raise ValueError(f"Invalid frontmatter in issue {issue_id}")

        fm_str = "".join(fm_lines)
        try:
            fm = yaml.safe_load(fm_str)
        except yaml.YAMLError as exc:
            raise ValueError(f"Invalid frontmatter in issue {issue_id}") from exc
        if not isinstance(fm, dict):
            raise ValueError(f"Invalid frontmatter in issue {issue_id}")

        # The description starts after the closing '---' line.
        description = "".join(lines[i + 1 :]).strip()
        return fm, description

    # ------------------------------------------------------------------
    # IssueAdapter interface
    # ------------------------------------------------------------------

    def create_issue(self, title: str, description: str, labels: list[str] | None = None) -> IssueResult:
        """Create a new markdown issue file."""
        self._issues_dir.mkdir(parents=True, exist_ok=True)
        issue_id = self._next_id()
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        frontmatter: dict = {
            "id": issue_id,
            "title": title,
            "status": "open",
            "labels": labels or [],
            "created_at": now,
            "comments": [],
        }
        self._write_issue(self._issues_dir / f"{issue_id}.md", frontmatter, description)
        return IssueResult(issue_id=issue_id, url="")

    def get_issue(self, issue_id: str) -> IssueDetail:
        """Read a markdown issue file and return an :class:`IssueDetail`."""
        path = self._issues_dir / f"{issue_id}.md"
        if not path.exists():
            raise FileNotFoundError(f"Issue {issue_id} not found")

        fm, description = self._read_issue(path, issue_id)

        raw_comments = fm.get("comments")
        if raw_comments is None:
            raw_comments = []
        elif not isinstance(raw_comments, list):
            raise ValueError(
                f"Issue {issue_id}: 'comments' frontmatter must be a list, got {type(raw_comments).__name__}"
            )

        comments: list[Comment] = []
        for c in raw_comments:
            if not isinstance(c, dict):
                raise ValueError(
                    f"Issue {issue_id}: each entry in 'comments' must be a mapping, got {type(c).__name__}"
                )
            comments.append(
                Comment(
                    comment_id=str(c.get("id", "")),
                    body=_coerce_str(c.get("body", "")),
                    created_at=_coerce_str(c.get("created_at", "")),
                )
            )

        raw_labels = fm.get("labels")
        if raw_labels is None:
            labels: list[str] = []
        elif isinstance(raw_labels, list):
            # Coerce non-string entries to str, skip None values.
            labels = [str(v) for v in raw_labels if v is not None]
        else:
            raise ValueError(f"Issue {issue_id}: 'labels' frontmatter must be a list, got {type(raw_labels).__name__}")

        # Always use the filename stem as canonical issue_id.  YAML may
        # parse unquoted ``id: 001`` as ``int(1)`` and lose zero-padding,
        # making the returned ID inconsistent with the file-based lookup.
        return IssueDetail(
            issue_id=issue_id,
            title=_coerce_str(fm.get("title", "")),
            description=description,
            status=_coerce_str(fm.get("status", "")),
            labels=labels,
            url="",
            comments=comments,
        )

    def add_comment(self, issue_id: str, comment: str) -> CommentResult:
        """Append a comment to an existing markdown issue file."""
        path = self._issues_dir / f"{issue_id}.md"
        if not path.exists():
            raise FileNotFoundError(f"Issue {issue_id} not found")

        fm, description = self._read_issue(path, issue_id)
        existing_comments = fm.get("comments")
        if existing_comments is None:
            existing_comments = []
        elif not isinstance(existing_comments, list):
            raise ValueError(
                f"Issue {issue_id}: 'comments' frontmatter must be a list, got {type(existing_comments).__name__}"
            )
        # Validate each existing entry is a mapping so we don't silently
        # append a dict next to a non-dict and corrupt the file.
        for entry in existing_comments:
            if not isinstance(entry, dict):
                raise ValueError(
                    f"Issue {issue_id}: each entry in 'comments' must be a mapping, got {type(entry).__name__}"
                )
        next_num = len(existing_comments) + 1
        new_id = f"c{next_num}"
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        existing_comments.append({"id": new_id, "body": comment, "created_at": now})
        fm["comments"] = existing_comments

        self._write_issue(path, fm, description)
        return CommentResult(comment_id=new_id)

    def list_issues(self, filters: IssueFilters | None = None) -> list[IssueSummary]:
        """List all non-archived markdown issues, optionally filtered."""
        if not self._issues_dir.exists():
            return []

        summaries: list[IssueSummary] = []
        for md_file in sorted(self._issues_dir.glob("*.md")):
            if not _ID_PATTERN.match(md_file.stem):
                continue
            try:
                fm, _ = self._read_issue(md_file, md_file.stem)
            except (ValueError, OSError):
                continue

            raw_labels = fm.get("labels")
            # Normalize to list[str] — coerce non-string entries to str and
            # skip None, matching get_issue() behaviour.
            issue_labels: list[str] = (
                [str(v) for v in raw_labels if v is not None] if isinstance(raw_labels, list) else []
            )

            if filters:
                state_filter = filters.get("state")
                if state_filter and _coerce_str(fm.get("status", "")) != state_filter:
                    continue
                label_filter = filters.get("labels")
                if label_filter and not set(label_filter) & set(issue_labels):
                    continue

            # Always use the filename stem as canonical issue_id (see
            # get_issue — YAML may drop zero-padding from ``id: 001``).
            summaries.append(
                IssueSummary(
                    issue_id=md_file.stem,
                    title=_coerce_str(fm.get("title", "")),
                    status=_coerce_str(fm.get("status", "")),
                    labels=issue_labels,
                    url="",
                )
            )
        return summaries
