"""Activity log tracking for persist-commit deduplication.

Provides local file-based tracking of which persist commits have been
posted as comments to PR threads and Jira.  The log is persisted at
``get_state_dir() / "activity-log" / "activity-log.json"`` and writes
call ``mark_dirty()`` so the auto-persist hook picks up changes.
"""

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from ..state import get_state_dir, get_value

ACTIVITY_LOG_DIR = "activity-log"
ACTIVITY_LOG_FILENAME = "activity-log.json"


@dataclass
class ActivityLogEntry:
    """A single posted-commit record in the activity log.

    Attributes:
        postedUtc: ISO-8601 UTC timestamp when the comment was posted.
        branchName: The source branch name associated with the persist commit.
        worktreeKey: The worktree key that produced the commit.
        prCommentPosted: Whether a PR comment was posted for this commit.
        jiraCommentPosted: Whether a Jira comment was posted for this commit.
        prId: Optional pull request ID associated with the comment.
    """

    postedUtc: str
    branchName: str
    worktreeKey: str
    prCommentPosted: bool
    jiraCommentPosted: bool
    prId: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the entry to a dictionary.

        Returns:
            Dictionary representation of this entry.
        """
        return {
            "postedUtc": self.postedUtc,
            "branchName": self.branchName,
            "worktreeKey": self.worktreeKey,
            "prCommentPosted": self.prCommentPosted,
            "jiraCommentPosted": self.jiraCommentPosted,
            "prId": self.prId,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActivityLogEntry":
        """Deserialize an entry from a dictionary.

        Args:
            data: Dictionary containing the entry fields.

        Returns:
            A new ``ActivityLogEntry`` instance.
        """
        return cls(
            postedUtc=data["postedUtc"],
            branchName=data["branchName"],
            worktreeKey=data["worktreeKey"],
            prCommentPosted=data["prCommentPosted"],
            jiraCommentPosted=data["jiraCommentPosted"],
            prId=data.get("prId"),
        )


@dataclass
class ActivityLog:
    """Root-level activity log tracking posted persist commits.

    Attributes:
        postedCommits: Dictionary keyed by commit hash, each value an
            ``ActivityLogEntry`` recording when and where the commit was
            posted.
    """

    postedCommits: Dict[str, ActivityLogEntry] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the activity log to a dictionary.

        Returns:
            Dictionary representation of the full activity log.
        """
        return {
            "postedCommits": {k: v.to_dict() for k, v in self.postedCommits.items()},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActivityLog":
        """Deserialize an activity log from a dictionary.

        Args:
            data: Dictionary containing the activity log fields.

        Returns:
            A new ``ActivityLog`` instance.
        """
        raw_commits = data.get("postedCommits", {})
        if not isinstance(raw_commits, dict):
            raw_commits = {}

        posted_commits: Dict[str, ActivityLogEntry] = {}
        for commit_hash, entry_data in raw_commits.items():
            if not isinstance(entry_data, dict):
                # Skip malformed entries with unexpected types rather than failing the entire load.
                continue
            try:
                posted_commits[commit_hash] = ActivityLogEntry.from_dict(entry_data)
            except (KeyError, TypeError):
                # Skip malformed entries missing required fields rather than failing the entire load.
                continue

        return cls(postedCommits=posted_commits)

    def has_been_posted(self, commit_hash: str) -> bool:
        """Check whether a persist commit has already been posted.

        Args:
            commit_hash: The commit SHA to look up.

        Returns:
            ``True`` if *commit_hash* is recorded in :attr:`postedCommits`
            and at least one of :attr:`ActivityLogEntry.prCommentPosted`
            or :attr:`ActivityLogEntry.jiraCommentPosted` is ``True``.
        """
        entry = self.postedCommits.get(commit_hash)
        if entry is None:
            return False
        return bool(entry.prCommentPosted or entry.jiraCommentPosted)

    def mark_as_posted(
        self,
        commit_hash: str,
        *,
        posted_utc: str,
        branch_name: str,
        worktree_key: str,
        pr_comment_posted: bool = False,
        jira_comment_posted: bool = False,
        pr_id: Optional[int] = None,
    ) -> None:
        """Record a persist commit as having been posted.

        Creates an :class:`ActivityLogEntry` and stores it under
        *commit_hash* in :attr:`postedCommits`.  If an entry already
        exists for the same hash, it is overwritten (latest metadata wins).

        .. note::

           This method does **not** call :func:`save_activity_log` or
           ``mark_dirty()`` — the caller is responsible for persisting
           after mutations.

        Args:
            commit_hash: The commit SHA to record.
            posted_utc: ISO-8601 UTC timestamp of the posting.
            branch_name: Source branch name.
            worktree_key: Worktree key that produced the commit.
            pr_comment_posted: Whether a PR comment was posted.
            jira_comment_posted: Whether a Jira comment was posted.
            pr_id: Optional pull request ID.
        """
        self.postedCommits[commit_hash] = ActivityLogEntry(
            postedUtc=posted_utc,
            branchName=branch_name,
            worktreeKey=worktree_key,
            prCommentPosted=pr_comment_posted,
            jiraCommentPosted=jira_comment_posted,
            prId=pr_id,
        )


def get_activity_log_file_path() -> Path:
    """Get the path to the activity-log.json file.

    The path is scoped by identity and worktree key via
    :func:`~agentic_devtools.state.get_state_dir`.

    Returns:
        Path to ``activity-log/activity-log.json`` under the state directory.
    """
    return get_state_dir() / ACTIVITY_LOG_DIR / ACTIVITY_LOG_FILENAME


def save_activity_log(log: ActivityLog) -> None:
    """Save the activity log to disk and signal the auto-persist hook.

    Creates parent directories if necessary, writes the JSON file with
    UTF-8 encoding, and calls ``mark_dirty()`` so the auto-persist hook
    commits the change to the ``-agdt`` branch.

    Args:
        log: The ``ActivityLog`` to persist.
    """
    file_path = get_activity_log_file_path()
    file_path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(log.to_dict(), indent=2, ensure_ascii=False)
    file_path.write_text(content, encoding="utf-8")

    # Signal that activity log has been mutated for auto-persist.
    try:
        from .git.agdt_branch import mark_dirty

        mark_dirty()
    except ImportError:
        pass  # agdt_branch not available (e.g., minimal install)


def _load_from_branch(
    source_branch: Optional[str],
    worktree_key: Optional[str],
) -> Optional[dict]:
    """Attempt to load activity-log.json from the -agdt branch.

    Returns the parsed dict if found, or ``None`` if unavailable.
    Expected failure modes (import unavailable, worktree resolution,
    git plumbing, JSON parsing) are caught individually.
    """
    try:
        from .git.agdt_branch import (
            GitPlumbingError,
            load_workflow_artifacts,
            resolve_worktree_key,
        )
    except ImportError:
        return None

    try:
        # Resolve source_branch
        effective_branch = source_branch
        if not effective_branch:
            effective_branch = get_value("sourceCodeHostingPlatform.pullRequest.sourceBranch")
        if not effective_branch:
            effective_branch = get_value("versionControl.currentBranch")
        if not effective_branch or not str(effective_branch).strip():
            return None
        effective_branch = str(effective_branch).strip()

        # Resolve worktree_key — raises ValueError when unresolvable
        effective_key = worktree_key
        if not effective_key:
            try:
                effective_key = resolve_worktree_key()
            except ValueError:
                return None

        artifacts = load_workflow_artifacts(
            source_branch=effective_branch,
            worktree_key=effective_key,
            workflow_type=ACTIVITY_LOG_DIR,
        )
        if artifacts is None:
            return None

        # Find the activity-log.json entry
        for path, file_content in artifacts.items():
            if path.endswith(ACTIVITY_LOG_FILENAME):
                if isinstance(file_content, dict):
                    return file_content
                if isinstance(file_content, str):
                    return json.loads(file_content)
        return None
    except (GitPlumbingError, json.JSONDecodeError, KeyError, TypeError):
        return None


def load_activity_log(
    *,
    fallback_to_branch: bool = True,
    source_branch: Optional[str] = None,
    worktree_key: Optional[str] = None,
) -> ActivityLog:
    """Load the activity log from disk, with optional branch fallback.

    Checks for a local file first.  When no local file exists and
    *fallback_to_branch* is ``True``, attempts to load from the
    ``-agdt`` branch via :func:`load_workflow_artifacts`.  Returns an
    empty :class:`ActivityLog` when nothing is found anywhere — this
    function **never** raises :exc:`FileNotFoundError`.

    Args:
        fallback_to_branch: If ``True`` (default), attempt to load from
            the ``-agdt`` branch when the local file is missing.
        source_branch: Optional source branch name for branch fallback.
            When ``None``, resolved from state
            (``sourceCodeHostingPlatform.pullRequest.sourceBranch`` or
            ``versionControl.currentBranch``).
        worktree_key: Optional worktree key for branch fallback.
            When ``None``, resolved via ``resolve_worktree_key()``.

    Returns:
        An :class:`ActivityLog` instance (possibly empty).
    """
    file_path = get_activity_log_file_path()

    if file_path.exists():
        try:
            content = file_path.read_text(encoding="utf-8")
            data = json.loads(content)
            return ActivityLog.from_dict(data)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
            print(
                f"Warning: failed to parse local activity log {file_path}: {exc}",
                file=sys.stderr,
            )

    # Local file not found or unreadable — attempt branch fallback
    if fallback_to_branch:
        try:
            data = _load_from_branch(source_branch, worktree_key)
        except Exception as exc:  # noqa: BLE001
            print(
                f"Warning: failed to load activity log from -agdt branch: {exc}",
                file=sys.stderr,
            )
            data = None
        if data is not None:
            return ActivityLog.from_dict(data)

    return ActivityLog()
