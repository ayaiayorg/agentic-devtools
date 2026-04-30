"""Test render_markdown function (FR-012, FR-013, FR-014, NFR-002)."""

from agentic_devtools.cli.speckit.pass_g.models import (
    Candidate,
    Finding,
    MatchStatus,
    Reference,
    ReferenceKind,
)
from agentic_devtools.cli.speckit.pass_g.reporter import render_markdown


def _make_finding(status: MatchStatus, candidates=None) -> Finding:
    ref = Reference("bad_ref", ReferenceKind.FUNCTION_NAME, "L42", "Use `bad_ref`")
    return Finding(
        reference=ref,
        status=status,
        candidates=candidates or [],
        explanation="test",
    )


def test_no_findings_success_message():
    md = render_markdown([])
    assert "✅" in md
    assert "No findings" in md


def test_only_matched_findings_success():
    findings = [_make_finding(MatchStatus.MATCHED)]
    md = render_markdown(findings)
    assert "✅" in md


def test_invalid_no_candidates_high_severity():
    findings = [_make_finding(MatchStatus.INVALID)]
    md = render_markdown(findings)
    assert "HIGH" in md


def test_invalid_with_candidates_medium_severity():
    candidate = Candidate("similar_ref", "file.py", 0.85, ReferenceKind.FUNCTION_NAME)
    findings = [_make_finding(MatchStatus.INVALID, candidates=[candidate])]
    md = render_markdown(findings)
    assert "MEDIUM" in md


def test_ambiguous_medium_severity():
    findings = [_make_finding(MatchStatus.AMBIGUOUS)]
    md = render_markdown(findings)
    assert "MEDIUM" in md


def test_performance_warning():
    findings = [_make_finding(MatchStatus.INVALID)]
    md = render_markdown(findings, elapsed_seconds=35.0)
    assert "Performance Warning" in md
    assert "35.0s" in md


def test_no_performance_warning_under_threshold():
    findings = [_make_finding(MatchStatus.INVALID)]
    md = render_markdown(findings, elapsed_seconds=10.0)
    assert "Performance Warning" not in md
