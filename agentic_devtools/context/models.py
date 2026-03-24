"""AgentContext data model for aggregated project context."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentContext:
    """Structured container for all context data aggregated by the retrieval layer.

    Holds issue details, validated file paths, recent Git changes, test
    coverage data, relevant documentation, and any non-fatal errors
    encountered during retrieval.
    """

    issue_key: str
    issue_details: dict | None = None
    parent_issue: dict | None = None
    epic_issue: dict | None = None
    remote_links: list = field(default_factory=list)
    relevant_files: list[str] = field(default_factory=list)
    recent_changes: list[dict] = field(default_factory=list)
    test_coverage: dict[str, Any] = field(default_factory=dict)
    documentation: list[dict[str, str]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Return a JSON-serializable dict representation."""
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> AgentContext:
        """Reconstruct an ``AgentContext`` from a dict.

        Missing keys fall back to the dataclass field defaults.
        Extra keys are silently ignored.
        """
        known_fields = {f.name for f in dataclasses.fields(cls)}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)
