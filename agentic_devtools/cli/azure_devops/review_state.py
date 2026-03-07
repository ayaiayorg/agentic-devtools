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


# Statuses that indicate a file/folder review is complete
COMPLETE_STATUSES = frozenset({ReviewStatus.APPROVED.value, ReviewStatus.NEEDS_WORK.value})


def compute_aggregate_status(statuses: List[str]) -> str:
    """Compute an aggregate status from a list of child statuses.

    This is the single source of truth for status derivation rules:
    - No statuses or all unreviewed → unreviewed
    - At least 1 started, not all complete → in-progress
    - All complete, all Approved → approved
    - All complete, any Needs Work → needs-work

    Args:
        statuses: List of status strings (ReviewStatus values).

    Returns:
        Derived aggregate status string.
    """
    if not statuses:
        return ReviewStatus.UNREVIEWED.value

    any_started = any(s != ReviewStatus.UNREVIEWED.value for s in statuses)
    all_complete = all(s in COMPLETE_STATUSES for s in statuses)

    if not any_started:
        return ReviewStatus.UNREVIEWED.value
    elif not all_complete:
        return ReviewStatus.IN_PROGRESS.value
    elif any(s == ReviewStatus.NEEDS_WORK.value for s in statuses):
        return ReviewStatus.NEEDS_WORK.value
    else:
        return ReviewStatus.APPROVED.value


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
    narrativeSummary: Optional[str] = None

    def to_dict(self) -> Dict:
        """Serialize to JSON-compatible dictionary."""
        return {
            "threadId": self.threadId,
            "commentId": self.commentId,
            "status": self.status,
            "narrativeSummary": self.narrativeSummary,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "OverallSummary":
        """Deserialize from a dictionary."""
        return cls(
            threadId=data["threadId"],
            commentId=data["commentId"],
            status=data.get("status", ReviewStatus.UNREVIEWED.value),
            narrativeSummary=data.get("narrativeSummary"),
        )


@dataclass
class FolderGroup:
    """Lightweight folder grouping — maps a folder name to its file paths.

    Unlike the former ``FolderEntry``, this class carries **no** Azure DevOps
    thread metadata (threadId / commentId / status).  Folder-level threads
    have been eliminated; folders are now lightweight groupings within the
    PR summary comment.
    """

    files: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Serialize to JSON-compatible dictionary."""
        return {
            "files": self.files,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "FolderGroup":
        """Deserialize from a dictionary.

        File paths in the files list are normalized to ensure leading slash.
        """
        return cls(
            files=[normalize_file_path(f) for f in data.get("files", [])],
        )


# Keep backward-compatible alias so downstream code that still references the
# old name does not break at import time.
FolderEntry = FolderGroup


class VerdictType:
    """Verdict types for multi-model reviews."""

    AGREE = "agree"
    SUPPLEMENT = "supplement"
    DISAGREE = "disagree"


class ConsolidationStatus:
    """Consolidation status for a file after all reviewers complete."""

    NOT_NEEDED = "not_needed"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"


CONSOLIDATION_TERMINAL = frozenset({ConsolidationStatus.NOT_NEEDED, ConsolidationStatus.COMPLETE})


@dataclass
class ModelVerdict:
    """Tracks an individual model's verdict for a file.

    Attributes:
        modelId: Model identifier (e.g. "Claude Opus 4.6").
        status: Review status for this model (unreviewed/in_progress/approved/needs_work).
        verdictType: Verdict classification (agree/supplement/disagree) or None if not yet complete.
    """

    modelId: str
    status: str = ReviewStatus.UNREVIEWED.value
    verdictType: Optional[str] = None

    def to_dict(self) -> Dict:
        """Serialize to JSON-compatible dictionary."""
        return {
            "modelId": self.modelId,
            "status": self.status,
            "verdictType": self.verdictType,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ModelVerdict":
        """Deserialize from a dictionary."""
        return cls(
            modelId=data["modelId"],
            status=data.get("status", ReviewStatus.UNREVIEWED.value),
            verdictType=data.get("verdictType"),
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
    previousSuggestions: Optional[List[SuggestionEntry]] = None
    suggestionVerificationStatus: Optional[str] = None
    modelVerdicts: List[ModelVerdict] = field(default_factory=list)
    consolidationStatus: Optional[str] = None

    def to_dict(self) -> Dict:
        """Serialize to JSON-compatible dictionary."""
        result = {
            "threadId": self.threadId,
            "commentId": self.commentId,
            "folder": self.folder,
            "fileName": self.fileName,
            "status": self.status,
            "summary": self.summary,
            "changeTrackingId": self.changeTrackingId,
            "suggestions": [s.to_dict() for s in self.suggestions],
            "previousSuggestions": (
                [s.to_dict() for s in self.previousSuggestions] if self.previousSuggestions is not None else None
            ),
            "suggestionVerificationStatus": self.suggestionVerificationStatus,
        }
        if self.modelVerdicts:
            result["modelVerdicts"] = [mv.to_dict() for mv in self.modelVerdicts]
        if self.consolidationStatus is not None:
            result["consolidationStatus"] = self.consolidationStatus
        return result

    @classmethod
    def from_dict(cls, data: Dict) -> "FileEntry":
        """Deserialize from a dictionary."""
        suggestions = [SuggestionEntry.from_dict(s) for s in data.get("suggestions", [])]
        raw_prev = data.get("previousSuggestions")
        previous = [SuggestionEntry.from_dict(s) for s in raw_prev] if raw_prev is not None else None
        model_verdicts = [ModelVerdict.from_dict(mv) for mv in data.get("modelVerdicts", [])]
        return cls(
            threadId=data["threadId"],
            commentId=data["commentId"],
            folder=data["folder"],
            fileName=data["fileName"],
            status=data.get("status", ReviewStatus.UNREVIEWED.value),
            summary=data.get("summary"),
            changeTrackingId=data.get("changeTrackingId"),
            suggestions=suggestions,
            previousSuggestions=previous,
            suggestionVerificationStatus=data.get("suggestionVerificationStatus"),
            modelVerdicts=model_verdicts,
            consolidationStatus=data.get("consolidationStatus"),
        )

    def get_model_verdict(self, model_id: str) -> Optional[ModelVerdict]:
        """Get the verdict entry for a specific model, or None if not found."""
        for mv in self.modelVerdicts:
            if mv.modelId == model_id:
                return mv
        return None

    def all_reviewers_complete(self) -> bool:
        """Return True if all configured reviewer models have a terminal verdict."""
        if not self.modelVerdicts:
            return False
        return all(mv.status in COMPLETE_STATUSES for mv in self.modelVerdicts)

    def has_disagreements(self) -> bool:
        """Return True if any reviewer posted a disagree or supplement verdict."""
        return any(mv.verdictType in (VerdictType.SUPPLEMENT, VerdictType.DISAGREE) for mv in self.modelVerdicts)

    def needs_consolidation(self) -> bool:
        """Return True if consolidation is needed (all reviewers done + disagreements exist)."""
        return self.all_reviewers_complete() and self.has_disagreements()


@dataclass
class ReviewSession:
    """Tracks an individual review session.

    Each session represents one AI agent reviewing the PR. Multiple sessions
    can exist for multi-model reviews or re-reviews.
    """

    sessionId: str
    modelId: str
    startedUtc: str
    completedUtc: Optional[str] = None
    status: str = "pending"
    commitHash: Optional[str] = None

    def to_dict(self) -> Dict:
        """Serialize to JSON-compatible dictionary."""
        return {
            "sessionId": self.sessionId,
            "modelId": self.modelId,
            "startedUtc": self.startedUtc,
            "completedUtc": self.completedUtc,
            "status": self.status,
            "commitHash": self.commitHash,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ReviewSession":
        """Deserialize from a dictionary."""
        return cls(
            sessionId=data["sessionId"],
            modelId=data["modelId"],
            startedUtc=data["startedUtc"],
            completedUtc=data.get("completedUtc"),
            status=data.get("status", "pending"),
            commitHash=data.get("commitHash"),
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
    folders: Dict[str, FolderGroup] = field(default_factory=dict)
    files: Dict[str, FileEntry] = field(default_factory=dict)
    commitHash: Optional[str] = None
    modelId: Optional[str] = None
    activityLogThreadId: int = 0
    sessions: List[ReviewSession] = field(default_factory=list)
    reviewerModels: Optional[List[str]] = None
    bossModel: Optional[str] = None

    def to_dict(self) -> Dict:
        """Serialize to JSON-compatible dictionary."""
        result = {
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
            "commitHash": self.commitHash,
            "modelId": self.modelId,
            "activityLogThreadId": self.activityLogThreadId,
            "sessions": [s.to_dict() for s in self.sessions],
        }
        if self.reviewerModels is not None:
            result["reviewerModels"] = list(self.reviewerModels)
        if self.bossModel is not None:
            result["bossModel"] = self.bossModel
        return result

    @classmethod
    def from_dict(cls, data: Dict) -> "ReviewState":
        """Deserialize from a dictionary.

        File dict keys are normalized to ensure leading slash consistency.
        Missing ``commitHash`` defaults to ``None`` for direct callers, but
        ``load_review_state()`` enforces migration — it deletes state files
        lacking ``commitHash`` and raises ``FileNotFoundError``.

        Multi-model fields (``reviewerModels``, ``bossModel``) default to
        ``None`` for backward compatibility with older state files.
        """
        overall_summary = OverallSummary.from_dict(data["overallSummary"])
        folders = {k: FolderGroup.from_dict(v) for k, v in data.get("folders", {}).items()}
        files = {normalize_file_path(k): FileEntry.from_dict(v) for k, v in data.get("files", {}).items()}
        sessions = [ReviewSession.from_dict(s) for s in data.get("sessions", [])]
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
            commitHash=data.get("commitHash"),
            modelId=data.get("modelId"),
            activityLogThreadId=data.get("activityLogThreadId", 0),
            sessions=sessions,
            reviewerModels=data.get("reviewerModels"),
            bossModel=data.get("bossModel"),
        )

    @property
    def is_multi_model(self) -> bool:
        """Return True if multiple reviewer models are configured."""
        return self.reviewerModels is not None and len(self.reviewerModels) > 1


def normalize_file_path(file_path: str) -> str:
    """
    Normalize a file path to ensure it has a leading slash and forward slashes.

    Args:
        file_path: The file path to normalize.

    Returns:
        Normalized path with leading slash and forward slashes.
    """
    file_path = file_path.replace("\\", "/")
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

    Implements migration detection: if the state file uses the old format
    (``FolderEntry`` with ``threadId`` fields or missing ``commitHash``),
    the file is deleted and ``FileNotFoundError`` is raised so the caller
    proceeds with a fresh scaffolding run.

    Args:
        pr_id: Pull request ID.

    Returns:
        ReviewState object.

    Raises:
        FileNotFoundError: If review-state.json does not exist for this PR,
            or if an incompatible old-format file was detected and deleted.
    """
    file_path = get_review_state_file_path(pr_id)
    if not file_path.exists():
        raise FileNotFoundError(f"Review state not found for PR {pr_id}: {file_path}")

    content = file_path.read_text(encoding="utf-8")
    data = json.loads(content)

    # Migration detection: old format lacks commitHash or has FolderEntry with threadId
    needs_migration = "commitHash" not in data
    if not needs_migration:
        for folder_data in data.get("folders", {}).values():
            if isinstance(folder_data, dict) and folder_data.get("threadId", 0) != 0:
                needs_migration = True
                break

    if needs_migration:
        print(f"Incompatible review state format detected for PR {pr_id}. Deleting and re-scaffolding.")
        file_path.unlink()
        raise FileNotFoundError(f"Review state not found for PR {pr_id}: {file_path}")

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


def get_folder_entry(review_state: ReviewState, folder_name: str) -> Optional[FolderGroup]:
    """
    Get a folder entry from review state by folder name.

    Args:
        review_state: ReviewState object.
        folder_name: Folder name.

    Returns:
        FolderGroup if found, None otherwise.
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
        status: New status value (must be a valid ReviewStatus value).
        summary: Optional new summary text.
        suggestions: Optional new suggestions list (replaces existing).

    Returns:
        Updated ReviewState.

    Raises:
        KeyError: If file not found in review state.
        ValueError: If status is not a valid ReviewStatus value.
    """
    valid_statuses = {s.value for s in ReviewStatus}
    if status not in valid_statuses:
        raise ValueError(f"Invalid status '{status}'. Must be one of: {sorted(valid_statuses)}")

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


def clear_suggestions_for_re_review(
    review_state: ReviewState,
    file_path: str,
) -> ReviewState:
    """
    Rotate current suggestions to previousSuggestions for a re-review.

    When a file is being re-reviewed (status is already "approved" or "needs-work"),
    the existing suggestions are moved to ``previousSuggestions`` as an audit trail
    and ``suggestions`` is cleared so that new suggestion threads can be created
    fresh.  Old threads in Azure DevOps are NOT resolved — only the local state
    pointer is cleared.

    The rotation fires when **both** conditions are met:

    1. Status is terminal (``approved`` or ``needs-work``).
    2. ``previousSuggestions is None`` (no prior rotation yet).

    Using ``None`` (not ``[]``) as the sentinel avoids a retry-safety bug: even
    when a terminal file had zero old suggestions, the rotation sets
    ``previousSuggestions = []`` which is distinct from ``None``, so a subsequent
    retry will correctly skip rotation and preserve any partially-accumulated new
    suggestions.

    Args:
        review_state: ReviewState object (mutated in-place).
        file_path: File path whose suggestions should be rotated.

    Returns:
        Updated ReviewState.

    Raises:
        KeyError: If file not found in review state.
    """
    normalized = normalize_file_path(file_path)
    if normalized not in review_state.files:
        raise KeyError(f"File not found in review state: {normalized}")

    file_entry = review_state.files[normalized]
    re_review_statuses = {ReviewStatus.APPROVED.value, ReviewStatus.NEEDS_WORK.value}

    # Only rotate when entering a fresh re-review (previousSuggestions is None).
    # Once rotation fires — even with an empty suggestions list — previousSuggestions
    # is set to [] (not None), so a subsequent retry won't re-trigger the rotation
    # and accidentally wipe partially-accumulated new suggestions.
    if file_entry.status in re_review_statuses and file_entry.previousSuggestions is None:
        file_entry.previousSuggestions = list(file_entry.suggestions)
        file_entry.suggestions = []

    return review_state
