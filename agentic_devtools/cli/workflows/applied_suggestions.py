"""Applied suggestions tracking for the apply-pull-request-review-suggestions workflow.

Provides a local file-based record of which review suggestions have been
applied, skipped, or deferred.  The state is persisted at
``get_state_dir() / "apply-suggestions" / "applied-suggestions.json"``
and writes call ``mark_dirty()`` so the auto-persist hook picks up changes.
"""

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ... import state as _state_module

APPLY_SUGGESTIONS_SUBDIR = "apply-suggestions"
APPLIED_SUGGESTIONS_FILENAME = "applied-suggestions.json"


@dataclass
class AppliedSuggestionEntry:
    """A single suggestion application record.

    Attributes:
        suggestionId: Identifier for the suggestion (e.g. thread ID or index).
        filePath: The file path the suggestion targets.
        status: One of ``"applied"``, ``"skipped"``, ``"deferred"``.
        appliedUtc: ISO-8601 UTC timestamp when the suggestion was applied.
        notes: Optional notes from the agent about the resolution.
    """

    suggestionId: str
    filePath: str
    status: str = "applied"
    appliedUtc: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "suggestionId": self.suggestionId,
            "filePath": self.filePath,
            "status": self.status,
            "appliedUtc": self.appliedUtc,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppliedSuggestionEntry":
        """Create from dictionary."""
        return cls(
            suggestionId=str(data.get("suggestionId", "")),
            filePath=str(data.get("filePath", "")),
            status=str(data.get("status", "applied")),
            appliedUtc=str(data.get("appliedUtc", "")),
            notes=str(data.get("notes", "")),
        )


@dataclass
class AppliedSuggestionsState:
    """Tracks which suggestions have been applied during an apply-suggestions workflow.

    Attributes:
        prId: The pull request ID being addressed.
        entries: List of suggestion application records.
        reviewStateSnapshot: Optional copy of the review-state.json at
            workflow initiation time (for cross-workflow reference).
    """

    prId: int = 0
    entries: list[AppliedSuggestionEntry] = field(default_factory=list)
    reviewStateSnapshot: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result: dict[str, Any] = {
            "prId": self.prId,
            "entries": [e.to_dict() for e in self.entries],
        }
        if self.reviewStateSnapshot is not None:
            result["reviewStateSnapshot"] = self.reviewStateSnapshot
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppliedSuggestionsState":
        """Create from dictionary."""
        entries = [AppliedSuggestionEntry.from_dict(e) for e in data.get("entries", [])]
        return cls(
            prId=int(data.get("prId", 0)),
            entries=entries,
            reviewStateSnapshot=data.get("reviewStateSnapshot"),
        )

    def add_entry(
        self,
        suggestion_id: str,
        file_path: str,
        status: str = "applied",
        applied_utc: str = "",
        notes: str = "",
    ) -> AppliedSuggestionEntry:
        """Add a new suggestion application entry.

        Args:
            suggestion_id: Identifier for the suggestion.
            file_path: The file path the suggestion targets.
            status: One of ``"applied"``, ``"skipped"``, ``"deferred"``.
            applied_utc: ISO-8601 UTC timestamp.
            notes: Optional notes from the agent.

        Returns:
            The newly created entry.
        """
        entry = AppliedSuggestionEntry(
            suggestionId=suggestion_id,
            filePath=file_path,
            status=status,
            appliedUtc=applied_utc,
            notes=notes,
        )
        self.entries.append(entry)
        return entry


def get_applied_suggestions_file_path() -> Path:
    """Get the path to the applied-suggestions.json file.

    The path is scoped by identity and worktree key via
    :func:`~agentic_devtools.state.get_state_dir`.

    Returns:
        Path to ``apply-suggestions/applied-suggestions.json`` under the
        state directory.
    """
    return _state_module.get_state_dir() / APPLY_SUGGESTIONS_SUBDIR / APPLIED_SUGGESTIONS_FILENAME


def save_applied_suggestions_state(state: AppliedSuggestionsState) -> None:
    """Save applied-suggestions state to disk and signal the auto-persist hook.

    Creates parent directories if necessary, writes the JSON file with
    UTF-8 encoding, and calls ``mark_dirty()`` so the auto-persist hook
    commits the change to the ``-agdt`` branch.

    Args:
        state: The ``AppliedSuggestionsState`` to persist.
    """
    file_path = get_applied_suggestions_file_path()
    file_path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(state.to_dict(), indent=2, ensure_ascii=False)
    file_path.write_text(content, encoding="utf-8")

    # Signal that applied-suggestions state has been mutated for auto-persist.
    try:
        from ..git.agdt_branch import mark_dirty

        mark_dirty()
    except ImportError:
        pass  # agdt_branch not available (e.g., minimal install)


def load_applied_suggestions_state(
    *,
    fallback_to_branch: bool = True,
    source_branch: str | None = None,
    worktree_key: str | None = None,
) -> AppliedSuggestionsState | None:
    """Load applied-suggestions state from disk, with optional branch fallback.

    Reads from the local ``apply-suggestions/applied-suggestions.json``
    file first.  When ``fallback_to_branch`` is True and the local file
    does not exist, attempts to load from the ``-agdt`` branch via
    :func:`~agentic_devtools.cli.git.agdt_branch.load_workflow_artifacts`.

    Args:
        fallback_to_branch: When True, try loading from the ``-agdt``
            branch if the local file is missing.
        source_branch: Source branch name for the ``-agdt`` branch lookup.
            Auto-resolved from state when ``None``.
        worktree_key: Worktree key for the ``-agdt`` branch lookup.
            Auto-resolved when ``None``.

    Returns:
        ``AppliedSuggestionsState`` or ``None`` if not found.
    """
    file_path = get_applied_suggestions_file_path()
    if file_path.exists():
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            return AppliedSuggestionsState.from_dict(data)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError):
            # Treat any local read/parse/schema issues as "no state" and fall back.
            pass

    if fallback_to_branch:
        try:
            data = _load_from_branch(source_branch, worktree_key)
            if data is not None:
                return AppliedSuggestionsState.from_dict(data)
        except Exception:
            # Be defensive: branch artifacts may be missing, corrupted, or malformed.
            pass

    return None


def _load_from_branch(
    source_branch: str | None,
    worktree_key: str | None,
) -> dict | None:
    """Attempt to load applied-suggestions.json from the -agdt branch.

    Returns the parsed dict if found, or ``None`` if unavailable.
    """
    try:
        from ..git.agdt_branch import (
            GitPlumbingError,
            load_workflow_artifacts,
            resolve_worktree_key,
        )
    except ImportError:
        return None

    try:
        effective_branch = source_branch
        if not effective_branch:
            effective_branch = _state_module.get_value("sourceCodeHostingPlatform.pullRequest.sourceBranch")
        if not effective_branch:
            effective_branch = _state_module.get_value("versionControl.currentBranch")
        if not effective_branch or not str(effective_branch).strip():
            return None
        effective_branch = str(effective_branch).strip()

        effective_key = worktree_key
        if not effective_key:
            try:
                effective_key = resolve_worktree_key()
            except ValueError:
                return None

        artifacts = load_workflow_artifacts(
            source_branch=effective_branch,
            worktree_key=effective_key,
            workflow_type=APPLY_SUGGESTIONS_SUBDIR,
        )
        if artifacts is None:
            return None

        for path, file_content in artifacts.items():
            if path.endswith(APPLIED_SUGGESTIONS_FILENAME):
                if isinstance(file_content, dict):
                    return file_content
                if isinstance(file_content, str):
                    try:
                        return json.loads(file_content)
                    except json.JSONDecodeError:
                        pass
    except (GitPlumbingError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(
            f"[applied-suggestions] Warning: failed to load from -agdt branch: {exc}",
            file=sys.stderr,
        )

    return None
