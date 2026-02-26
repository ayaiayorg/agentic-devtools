"""Review state schema and CRUD functions for managing hierarchical PR review state.

Provides dataclasses for each schema level and load/save/update functions.
File location: scripts/temp/pull-request-review/prompts/{pr_id}/review-state.json
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from ...state import get_state_dir

REVIEW_STATE_DIR_PARTS = ("pull-request-review", "prompts")
REVIEW_STATE_FILENAME = "review-state.json"


class ReviewStatus(str, Enum):
    """Status values for PR review items."""

    UNREVIEWED = "unreviewed"
    IN_PROGRESS = "in-progress"
    APPROVED = "approved"
    NEEDS_WORK = "needs-work"


@dataclass
class SuggestionEntry:
    """A suggestion posted on a specific line/range of a file."""

    threadId: int
    commentId: int
    line: int
    endLine: int
    severity: str
    outOfScope: bool
    linkText: str
    content: str

    def to_dict(self) -> Dict:
        """Serialize to JSON-compatible dictionary."""
        return {
            "threadId": self.threadId,
            "commentId": self.commentId,
            "line": self.line,
            "endLine": self.endLine,
            "severity": self.severity,
            "outOfScope": self.outOfScope,
            "linkText": self.linkText,
            "content": self.content,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "SuggestionEntry":
        """Deserialize from a dictionary."""
        return cls(
            threadId=data["threadId"],
            commentId=data["commentId"],
            line=data["line"],
            endLine=data["endLine"],
            severity=data["severity"],
            outOfScope=data["outOfScope"],
            linkText=data["linkText"],
            content=data["content"],
        )


@dataclass
class OverallSummary:
    """Overall PR review summary metadata."""

    threadId: int
    commentId: int
    status: str = ReviewStatus.UNREVIEWED.value

    def to_dict(self) -> Dict:
        """Serialize to JSON-compatible dictionary."""
        return {
            "threadId": self.threadId,
            "commentId": self.commentId,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "OverallSummary":
        """Deserialize from a dictionary."""
        return cls(
            threadId=data["threadId"],
            commentId=data["commentId"],
            status=data.get("status", ReviewStatus.UNREVIEWED.value),
        )


@dataclass
class FolderEntry:
    """Review state for a folder grouping."""

    threadId: int
    commentId: int
    status: str = ReviewStatus.UNREVIEWED.value
    files: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Serialize to JSON-compatible dictionary."""
        return {
            "threadId": self.threadId,
            "commentId": self.commentId,
            "status": self.status,
            "files": self.files,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "FolderEntry":
        """Deserialize from a dictionary.

        File paths in the files list are normalized to ensure leading slash.
        """
        return cls(
            threadId=data["threadId"],
            commentId=data["commentId"],
            status=data.get("status", ReviewStatus.UNREVIEWED.value),
            files=[normalize_file_path(f) for f in data.get("files", [])],
        )


@dataclass
class FileEntry:
    """Review state for an individual file."""

    threadId: int
    commentId: int
    folder: str
    fileName: str
    status: str = ReviewStatus.UNREVIEWED.value
    summary: Optional[str] = None
    changeTrackingId: Optional[int] = None
    suggestions: List[SuggestionEntry] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Serialize to JSON-compatible dictionary."""
        return {
            "threadId": self.threadId,
            "commentId": self.commentId,
            "folder": self.folder,
            "fileName": self.fileName,
            "status": self.status,
            "summary": self.summary,
            "changeTrackingId": self.changeTrackingId,
            "suggestions": [s.to_dict() for s in self.suggestions],
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "FileEntry":
        """Deserialize from a dictionary."""
        suggestions = [SuggestionEntry.from_dict(s) for s in data.get("suggestions", [])]
        return cls(
            threadId=data["threadId"],
            commentId=data["commentId"],
            folder=data["folder"],
            fileName=data["fileName"],
            status=data.get("status", ReviewStatus.UNREVIEWED.value),
            summary=data.get("summary"),
            changeTrackingId=data.get("changeTrackingId"),
            suggestions=suggestions,
        )


@dataclass
class ReviewState:
    """Top-level PR review state."""

    prId: int
    repoId: str
    repoName: str
    project: str
    organization: str
    latestIterationId: int
    scaffoldedUtc: str
    overallSummary: OverallSummary
    folders: Dict[str, FolderEntry] = field(default_factory=dict)
    files: Dict[str, FileEntry] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Serialize to JSON-compatible dictionary."""
        return {
            "prId": self.prId,
            "repoId": self.repoId,
            "repoName": self.repoName,
            "project": self.project,
            "organization": self.organization,
            "latestIterationId": self.latestIterationId,
            "scaffoldedUtc": self.scaffoldedUtc,
            "overallSummary": self.overallSummary.to_dict(),
            "folders": {k: v.to_dict() for k, v in self.folders.items()},
            "files": {k: v.to_dict() for k, v in self.files.items()},
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ReviewState":
        """Deserialize from a dictionary.

        File dict keys are normalized to ensure leading slash consistency.
        """
        overall_summary = OverallSummary.from_dict(data["overallSummary"])
        folders = {k: FolderEntry.from_dict(v) for k, v in data.get("folders", {}).items()}
        files = {normalize_file_path(k): FileEntry.from_dict(v) for k, v in data.get("files", {}).items()}
        return cls(
            prId=data["prId"],
            repoId=data["repoId"],
            repoName=data["repoName"],
            project=data["project"],
            organization=data["organization"],
            latestIterationId=data["latestIterationId"],
            scaffoldedUtc=data["scaffoldedUtc"],
            overallSummary=overall_summary,
            folders=folders,
            files=files,
        )


def normalize_file_path(file_path: str) -> str:
    """
    Normalize a file path to ensure it has a leading slash.

    Args:
        file_path: The file path to normalize.

    Returns:
        Normalized path with leading slash.
    """
    if not file_path.startswith("/"):
        return "/" + file_path
    return file_path


def get_review_state_file_path(pr_id: int) -> Path:
    """
    Get the path to the review-state.json file for a PR.

    Args:
        pr_id: Pull request ID.

    Returns:
        Path to review-state.json.
    """
    return get_state_dir() / REVIEW_STATE_DIR_PARTS[0] / REVIEW_STATE_DIR_PARTS[1] / str(pr_id) / REVIEW_STATE_FILENAME


def load_review_state(pr_id: int) -> ReviewState:
    """
    Load review state from JSON file.

    Args:
        pr_id: Pull request ID.

    Returns:
        ReviewState object.

    Raises:
        FileNotFoundError: If review-state.json does not exist for this PR.
    """
    file_path = get_review_state_file_path(pr_id)
    if not file_path.exists():
        raise FileNotFoundError(f"Review state not found for PR {pr_id}: {file_path}")

    content = file_path.read_text(encoding="utf-8")
    data = json.loads(content)
    return ReviewState.from_dict(data)


def save_review_state(review_state: ReviewState) -> None:
    """
    Save review state to JSON file.

    Args:
        review_state: ReviewState object to save.
    """
    file_path = get_review_state_file_path(review_state.prId)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(review_state.to_dict(), indent=2, ensure_ascii=False)
    file_path.write_text(content, encoding="utf-8")


def get_file_entry(review_state: ReviewState, file_path: str) -> Optional[FileEntry]:
    """
    Get a file entry from review state by file path.

    Args:
        review_state: ReviewState object.
        file_path: File path (with or without leading slash).

    Returns:
        FileEntry if found, None otherwise.
    """
    normalized = normalize_file_path(file_path)
    return review_state.files.get(normalized)


def get_folder_entry(review_state: ReviewState, folder_name: str) -> Optional[FolderEntry]:
    """
    Get a folder entry from review state by folder name.

    Args:
        review_state: ReviewState object.
        folder_name: Folder name.

    Returns:
        FolderEntry if found, None otherwise.
    """
    return review_state.folders.get(folder_name)


def update_file_status(
    review_state: ReviewState,
    file_path: str,
    status: str,
    summary: Optional[str] = None,
    suggestions: Optional[List[SuggestionEntry]] = None,
) -> ReviewState:
    """
    Update the status (and optionally summary/suggestions) of a file in review state.

    Args:
        review_state: ReviewState object.
        file_path: File path to update.
        status: New status value.
        summary: Optional new summary text.
        suggestions: Optional new suggestions list (replaces existing).

    Returns:
        Updated ReviewState.

    Raises:
        KeyError: If file not found in review state.
    """
    normalized = normalize_file_path(file_path)
    if normalized not in review_state.files:
        raise KeyError(f"File not found in review state: {normalized}")

    file_entry = review_state.files[normalized]
    file_entry.status = status
    if summary is not None:
        file_entry.summary = summary
    if suggestions is not None:
        file_entry.suggestions = suggestions

    return review_state


def add_suggestion_to_file(
    review_state: ReviewState,
    file_path: str,
    suggestion: SuggestionEntry,
) -> ReviewState:
    """
    Add a suggestion to a file's suggestions list.

    Args:
        review_state: ReviewState object.
        file_path: File path to add suggestion to.
        suggestion: SuggestionEntry to add.

    Returns:
        Updated ReviewState.

    Raises:
        KeyError: If file not found in review state.
    """
    normalized = normalize_file_path(file_path)
    if normalized not in review_state.files:
        raise KeyError(f"File not found in review state: {normalized}")

    review_state.files[normalized].suggestions.append(suggestion)
    return review_state
