"""Reporter for E.2 — generates Test Coverage Summary table and findings.

Implements FR-007 (summary table) and FR-008 (actionable recommendations).
"""

from __future__ import annotations

from .models import FRCoverage, TestCoverageFinding


def render_test_coverage_summary(
    coverage: dict[str, FRCoverage],
) -> str:
    """Render the Test Coverage Summary table (FR-007).

    Columns: FR identifier, associated user story, test task IDs,
    detected test types, coverage status.
    """
    lines: list[str] = []
    lines.append("### Test Coverage Summary")
    lines.append("")
    lines.append("| FR | User Story | Test Task IDs | Test Types | Status |")
    lines.append("|------|------------|---------------|------------|--------|")

    for fr_id, cov in coverage.items():
        us = f"US{cov.fr_info.user_story}" if cov.fr_info.user_story else "N/A"
        task_ids = ", ".join(t.task_id for t in cov.test_tasks) or "None"
        test_types = ", ".join(cov.test_types) or "None"
        status = "✅ Covered" if cov.is_covered else "❌ Missing"
        lines.append(f"| {fr_id} | {us} | {task_ids} | {test_types} | {status} |")

    lines.append("")
    return "\n".join(lines)


def render_findings(
    findings: list[TestCoverageFinding],
) -> str:
    """Render findings as a markdown section (FR-008).

    Each finding includes severity, description, and actionable recommendation.
    Task-scoped findings are grouped in an "Unmapped Tasks" sub-section.
    """
    if not findings:
        return ""

    lines: list[str] = []
    lines.append("### E.2 Test Coverage Findings")
    lines.append("")

    # Separate FR-scoped from task-scoped findings
    fr_findings = [
        f
        for f in findings
        if f.key.startswith("FR-") or f.key.startswith("TASK:missing") or f.key.startswith("TASK:empty")
    ]
    task_findings = [
        f
        for f in findings
        if f.key.startswith("TASK:") and not f.key.startswith("TASK:missing") and not f.key.startswith("TASK:empty")
    ]

    if fr_findings:
        lines.append("| Severity | Key | Description | Recommendation |")
        lines.append("|----------|-----|-------------|----------------|")
        for finding in fr_findings:
            lines.append(f"| {finding.severity} | {finding.key} | {finding.description} | {finding.recommendation} |")
        lines.append("")

    if task_findings:
        lines.append("#### Unmapped Tasks")
        lines.append("")
        lines.append("| Severity | Key | Description | Recommendation |")
        lines.append("|----------|-----|-------------|----------------|")
        for finding in task_findings:
            lines.append(f"| {finding.severity} | {finding.key} | {finding.description} | {finding.recommendation} |")
        lines.append("")

    return "\n".join(lines)
