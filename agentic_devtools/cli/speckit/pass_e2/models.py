"""Data models for E.2 Test Coverage Validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TestTask:
    """A task identified as test-related from tasks.md."""

    task_id: str
    description: str
    fr_refs: list[str] = field(default_factory=list)
    us_labels: list[int] = field(default_factory=list)
    test_types: list[str] = field(default_factory=list)
    is_ambiguous: bool = False


@dataclass
class FRInfo:
    """Information about a functional requirement extracted from spec.md."""

    fr_id: str
    priority: int  # 1, 2, or 3 (P1, P2, P3)
    user_story: int | None = None  # 1-based user story index, or None
    priority_ambiguous: bool = False
    acceptance_scenarios: list[str] = field(default_factory=list)


@dataclass
class FRCoverage:
    """Coverage information for a single FR."""

    fr_info: FRInfo
    test_tasks: list[TestTask] = field(default_factory=list)
    test_types: list[str] = field(default_factory=list)
    has_happy_path: bool = False

    @property
    def is_covered(self) -> bool:
        """Return True if at least one test task covers this FR."""
        return len(self.test_tasks) > 0


@dataclass
class TestCoverageFinding:
    """A finding from the E.2 test coverage validation."""

    key: str  # Stable key, e.g. "FR-001:no-test-task" or "TASK:unmapped-test-task"
    severity: str  # "CRITICAL", "HIGH", or "LOW"
    fr_id: str | None = None  # FR identifier if FR-scoped
    description: str = ""
    recommendation: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable dict."""
        result: dict[str, Any] = {
            "key": self.key,
            "severity": self.severity,
            "description": self.description,
            "recommendation": self.recommendation,
        }
        if self.fr_id:
            result["fr_id"] = self.fr_id
        return result


@dataclass
class TestCoverageResult:
    """Complete result of E.2 test coverage validation."""

    findings: list[TestCoverageFinding] = field(default_factory=list)
    coverage: dict[str, FRCoverage] = field(default_factory=dict)
    summary_table: str = ""
    test_tasks: list[TestTask] = field(default_factory=list)
    unmapped_tasks: list[TestTask] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable dict for test-coverage.json output."""
        return {
            "findings": [f.to_dict() for f in self.findings],
            "coverage": {
                fr_id: {
                    "fr_id": cov.fr_info.fr_id,
                    "priority": cov.fr_info.priority,
                    "user_story": cov.fr_info.user_story,
                    "is_covered": cov.is_covered,
                    "has_happy_path": cov.has_happy_path,
                    "test_task_ids": [t.task_id for t in cov.test_tasks],
                    "test_types": cov.test_types,
                }
                for fr_id, cov in self.coverage.items()
            },
            "summary_table": self.summary_table,
            "summary": {
                "total_frs": len(self.coverage),
                "covered_frs": sum(1 for c in self.coverage.values() if c.is_covered),
                "uncovered_frs": sum(1 for c in self.coverage.values() if not c.is_covered),
                "total_test_tasks": len(self.test_tasks),
                "unmapped_test_tasks": len(self.unmapped_tasks),
                "total_findings": len(self.findings),
            },
        }
