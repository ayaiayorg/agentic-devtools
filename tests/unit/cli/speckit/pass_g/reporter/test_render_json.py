"""Test render_json function (FR-012, FR-013, NFR-004)."""

import json

from agentic_devtools.cli.speckit.pass_g.models import (
    Finding,
    MatchStatus,
    Reference,
    ReferenceKind,
)
from agentic_devtools.cli.speckit.pass_g.reporter import render_json


def _make_finding(status: MatchStatus) -> Finding:
    ref = Reference("test_ref", ReferenceKind.FUNCTION_NAME, "L1", "context")
    return Finding(reference=ref, status=status, explanation="test")


def test_json_structure():
    findings = [_make_finding(MatchStatus.INVALID)]
    result = json.loads(render_json(findings))
    assert result["pass"] == "G"
    assert result["title"] == "Code Reference Cross-Referencing"
    assert "findings" in result
    assert "summary" in result


def test_json_distinguishes_statuses():
    findings = [
        _make_finding(MatchStatus.INVALID),
        _make_finding(MatchStatus.AMBIGUOUS),
        _make_finding(MatchStatus.SKIPPED),
    ]
    result = json.loads(render_json(findings))
    statuses = {f["status"] for f in result["findings"]}
    assert "invalid" in statuses
    assert "ambiguous" in statuses
    assert "skipped" in statuses


def test_json_zero_findings_success():
    result = json.loads(render_json([]))
    assert result["total_references"] == 0
    assert result["findings"] == []


def test_json_performance_warning():
    result = json.loads(render_json([], elapsed_seconds=35.0))
    assert "performance_warning" in result
