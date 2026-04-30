"""Test reporter — _severity_for and _suggestion_text edge cases."""

from agentic_devtools.cli.speckit.pass_g.models import (
    Candidate,
    Finding,
    MatchStatus,
    Reference,
    ReferenceKind,
)
from agentic_devtools.cli.speckit.pass_g.reporter import (
    _severity_for,
    _suggestion_text,
    render_markdown,
)


def _make_finding(status: MatchStatus, candidates=None) -> Finding:
    ref = Reference("test_ref", ReferenceKind.FUNCTION_NAME, "L1", "Use `test_ref`")
    return Finding(
        reference=ref,
        status=status,
        candidates=candidates or [],
        explanation="test explanation",
    )


def test_severity_partial_is_low():
    """PARTIAL status maps to LOW severity."""
    finding = _make_finding(MatchStatus.PARTIAL)
    assert _severity_for(finding) == "LOW"


def test_severity_skipped_is_low():
    """SKIPPED status maps to LOW severity."""
    finding = _make_finding(MatchStatus.SKIPPED)
    assert _severity_for(finding) == "LOW"


def test_severity_matched_is_low():
    """MATCHED status (fallback) maps to LOW severity."""
    finding = _make_finding(MatchStatus.MATCHED)
    assert _severity_for(finding) == "LOW"


def test_suggestion_text_no_candidates():
    """No candidates produces 'no reliable suggestion' message."""
    finding = _make_finding(MatchStatus.INVALID)
    result = _suggestion_text(finding)
    assert "No reliable suggestion" in result


def test_suggestion_text_single_candidate():
    """Single candidate shows the candidate name and score."""
    candidate = Candidate("validate_frs", "src/mod.py", 0.92, ReferenceKind.FUNCTION_NAME)
    finding = _make_finding(MatchStatus.INVALID, candidates=[candidate])
    result = _suggestion_text(finding)
    assert "validate_frs" in result
    assert "0.92" in result
    assert "+0 more" not in result


def test_suggestion_text_multiple_candidates():
    """Multiple candidates shows count of additional candidates."""
    candidates = [
        Candidate("validate_frs", "src/mod.py", 0.92, ReferenceKind.FUNCTION_NAME),
        Candidate("validate_nfrs", "src/mod2.py", 0.88, ReferenceKind.FUNCTION_NAME),
        Candidate("validate_all", "src/mod3.py", 0.80, ReferenceKind.FUNCTION_NAME),
    ]
    finding = _make_finding(MatchStatus.INVALID, candidates=candidates)
    result = _suggestion_text(finding)
    assert "validate_frs" in result
    assert "+2 more" in result


def test_render_markdown_partial_finding():
    """PARTIAL findings appear in the Markdown table with LOW severity."""
    finding = _make_finding(MatchStatus.PARTIAL)
    md = render_markdown([finding])
    assert "LOW" in md
    assert "Code Reference" in md


def test_render_markdown_skipped_finding():
    """SKIPPED findings appear in the Markdown table with LOW severity."""
    finding = _make_finding(MatchStatus.SKIPPED)
    md = render_markdown([finding])
    assert "LOW" in md
