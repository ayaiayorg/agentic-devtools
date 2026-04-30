"""Structured finding output — Markdown and JSON (FR-012, FR-013, FR-014)."""

from __future__ import annotations

import json
from typing import Any

from .constants import PERFORMANCE_WARNING_SECONDS
from .models import Finding, MatchStatus


def render_markdown(
    findings: list[Finding],
    elapsed_seconds: float = 0.0,
    plan_filename: str = "plan.md",
) -> str:
    """Render findings as a Markdown table (FR-012, FR-013, FR-014, NFR-002).

    Severity mapping:
        INVALID with no candidates → HIGH
        INVALID with candidates → MEDIUM (correctable)
        AMBIGUOUS → MEDIUM
        PARTIAL → LOW
        SKIPPED → LOW (informational)
    """
    lines: list[str] = []
    lines.append("## Pass G: Code Reference Cross-Referencing\n")

    if elapsed_seconds > PERFORMANCE_WARNING_SECONDS:
        lines.append(
            f"⚠️ **Performance Warning**: Pass G took {elapsed_seconds:.1f}s "
            f"(threshold: {PERFORMANCE_WARNING_SECONDS}s)\n"
        )

    if not findings:
        lines.append("✅ All code references resolved successfully. No findings.\n")
        return "\n".join(lines)

    # Only report non-matched, non-new-symbol findings
    reportable = [f for f in findings if f.status not in (MatchStatus.MATCHED, MatchStatus.NEW_SYMBOL)]

    if not reportable:
        lines.append("✅ All code references resolved successfully. No findings.\n")
        return "\n".join(lines)

    lines.append("| # | Category | Severity | Location | Description | Suggestion |")
    lines.append("|---|----------|----------|----------|-------------|------------|")

    for i, finding in enumerate(reportable, start=1):
        severity = _severity_for(finding)
        location = f"{plan_filename}:{finding.reference.plan_location}"
        description = finding.explanation
        suggestion = _suggestion_text(finding)
        lines.append(f"| F-{i:02d} | Code Reference | {severity} | {location} | {description} | {suggestion} |")

    lines.append("")
    return "\n".join(lines)


def render_json(findings: list[Finding], elapsed_seconds: float = 0.0) -> str:
    """Render findings as structured JSON (FR-012, FR-013, NFR-004).

    Includes all findings (including MATCHED and NEW_SYMBOL for completeness).
    """
    output: dict[str, Any] = {
        "pass": "G",
        "title": "Code Reference Cross-Referencing",
        "elapsed_seconds": round(elapsed_seconds, 2),
        "total_references": len(findings),
        "findings": [f.to_dict() for f in findings],
        "summary": _build_summary(findings),
    }

    if elapsed_seconds > PERFORMANCE_WARNING_SECONDS:
        output["performance_warning"] = (
            f"Elapsed {elapsed_seconds:.1f}s exceeds {PERFORMANCE_WARNING_SECONDS}s threshold"
        )

    return json.dumps(output, indent=2)


def _severity_for(finding: Finding) -> str:
    """Map finding status to severity level."""
    if finding.status == MatchStatus.INVALID:
        if finding.candidates:
            return "MEDIUM"
        return "HIGH"
    if finding.status == MatchStatus.AMBIGUOUS:
        return "MEDIUM"
    if finding.status in (MatchStatus.PARTIAL, MatchStatus.SKIPPED):
        return "LOW"
    return "LOW"


def _suggestion_text(finding: Finding) -> str:
    """Build human-readable suggestion text."""
    if not finding.candidates:
        return "No reliable suggestion found"
    top = finding.candidates[0]
    text = f"Nearest match: `{top.symbol_name}` (score: {top.similarity_score:.2f})"
    if len(finding.candidates) > 1:
        text += f" (+{len(finding.candidates) - 1} more)"
    return text


def _build_summary(findings: list[Finding]) -> dict[str, int]:
    """Build a counts summary by status."""
    summary: dict[str, int] = {}
    for f in findings:
        key = f.status.value
        summary[key] = summary.get(key, 0) + 1
    return summary
