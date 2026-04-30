"""Test Finding dataclass (FR-013, FR-014)."""

from agentic_devtools.cli.speckit.pass_g.models import (
    Candidate,
    Finding,
    MatchStatus,
    Reference,
    ReferenceKind,
)


def test_finding_fields():
    ref = Reference(
        text="nonexistent_func",
        kind=ReferenceKind.FUNCTION_NAME,
        plan_location="L10",
        context_sentence="Call `nonexistent_func`",
    )
    finding = Finding(
        reference=ref,
        status=MatchStatus.INVALID,
        candidates=[],
        confidence_level="none",
        explanation="Not found.",
    )
    assert finding.reference is ref
    assert finding.status == MatchStatus.INVALID
    assert finding.candidates == []
    assert finding.confidence_level == "none"
    assert finding.explanation == "Not found."


def test_finding_to_dict():
    ref = Reference(
        text="some_func",
        kind=ReferenceKind.FUNCTION_NAME,
        plan_location="L5",
        context_sentence="Use `some_func` here",
    )
    candidate = Candidate(
        symbol_name="some_function",
        file_path="src/mod.py",
        similarity_score=0.88,
        kind=ReferenceKind.FUNCTION_NAME,
    )
    finding = Finding(
        reference=ref,
        status=MatchStatus.INVALID,
        candidates=[candidate],
        confidence_level="low",
        explanation="Nearest match: some_function",
    )
    d = finding.to_dict()
    assert d["reference"]["text"] == "some_func"
    assert d["reference"]["kind"] == "function_name"
    assert d["reference"]["plan_location"] == "L5"
    assert d["status"] == "invalid"
    assert len(d["candidates"]) == 1
    assert d["candidates"][0]["symbol_name"] == "some_function"
    assert d["candidates"][0]["similarity_score"] == 0.88
    assert d["confidence_level"] == "low"


def test_finding_to_dict_stable_output():
    """Verify serialized finding includes all expected keys (FR-013, FR-016)."""
    ref = Reference(
        text="missing",
        kind=ReferenceKind.UNCLASSIFIED,
        plan_location="L1",
        context_sentence="context",
    )
    finding = Finding(reference=ref, status=MatchStatus.SKIPPED)
    d = finding.to_dict()
    assert "reference" in d
    assert "status" in d
    assert "candidates" in d
    assert "confidence_level" in d
    assert "explanation" in d
