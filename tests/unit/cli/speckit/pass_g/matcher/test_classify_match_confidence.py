"""Test classify_match_confidence function (FR-009, FR-010)."""

from agentic_devtools.cli.speckit.pass_g.matcher import classify_match_confidence
from agentic_devtools.cli.speckit.pass_g.models import Candidate, ReferenceKind


def _candidate(score: float, name: str = "sym") -> Candidate:
    return Candidate(name, "file.py", score, ReferenceKind.FUNCTION_NAME)


def test_high_confidence_single_top():
    candidates = [_candidate(0.95)]
    assert classify_match_confidence(candidates) == "high"


def test_high_confidence_with_distant_second():
    candidates = [_candidate(0.95), _candidate(0.80)]
    assert classify_match_confidence(candidates) == "high"


def test_ambiguous_multiple_within_margin():
    candidates = [_candidate(0.92), _candidate(0.90)]
    assert classify_match_confidence(candidates) == "ambiguous"


def test_ambiguous_below_high_threshold():
    candidates = [_candidate(0.80), _candidate(0.78)]
    assert classify_match_confidence(candidates) == "ambiguous"


def test_low_confidence():
    candidates = [_candidate(0.80), _candidate(0.70)]
    assert classify_match_confidence(candidates) == "low"


def test_no_candidates():
    assert classify_match_confidence([]) == "none"
