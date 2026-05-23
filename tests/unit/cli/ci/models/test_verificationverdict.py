"""Tests for VerificationVerdict enum."""

from agentic_devtools.cli.ci.models import VerificationVerdict


class TestVerificationVerdict:
    """Tests for the VerificationVerdict enum."""

    def test_comment_resolve_value(self) -> None:
        assert VerificationVerdict.COMMENT_RESOLVE.value == "COMMENT_RESOLVE"

    def test_comment_unresolve_value(self) -> None:
        assert VerificationVerdict.COMMENT_UNRESOLVE.value == "COMMENT_UNRESOLVE"

    def test_enum_has_exactly_two_members(self) -> None:
        assert len(VerificationVerdict) == 2
