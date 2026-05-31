"""Tests for ResolutionVerdict."""

from agentic_devtools.cli.ci.resolution.models import ResolutionVerdict


def test_values() -> None:
    assert ResolutionVerdict.RESOLVE.value == "RESOLVE"
    assert ResolutionVerdict.UNRESOLVE.value == "UNRESOLVE"
    assert ResolutionVerdict.TENTATIVE.value == "TENTATIVE"
    assert ResolutionVerdict.ABANDONED.value == "ABANDONED"


def test_from_string() -> None:
    assert ResolutionVerdict("RESOLVE") == ResolutionVerdict.RESOLVE
    assert ResolutionVerdict("UNRESOLVE") == ResolutionVerdict.UNRESOLVE
    assert ResolutionVerdict("TENTATIVE") == ResolutionVerdict.TENTATIVE
    assert ResolutionVerdict("ABANDONED") == ResolutionVerdict.ABANDONED
