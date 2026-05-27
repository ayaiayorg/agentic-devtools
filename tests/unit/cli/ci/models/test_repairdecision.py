"""Tests for RepairDecision dataclass."""

from agentic_devtools.cli.ci.models import CheckRunStatus, RepairDecision, ReviewCommentInfo

_COMMENT = ReviewCommentInfo(id=1, path="foo.py", body="fix this", html_url="https://github.com/r/p#1")


class TestRepairDecision:
    """Tests for the RepairDecision frozen dataclass."""

    def test_default_values(self) -> None:
        decision = RepairDecision()
        assert decision.repair_needed is False
        assert decision.repair_type == ""
        assert decision.review_id == 0
        assert decision.review_comments == ()
        assert decision.failed_checks == ()

    def test_custom_values(self) -> None:
        checks = (CheckRunStatus(id=1, name="ci", status="completed", conclusion="failure"),)
        decision = RepairDecision(
            repair_needed=True,
            repair_type="both",
            review_id=42,
            review_comments=(_COMMENT,),
            failed_checks=checks,
        )
        assert decision.repair_needed is True
        assert decision.repair_type == "both"
        assert decision.review_id == 42
        assert len(decision.review_comments) == 1
        assert decision.review_comments[0] == _COMMENT
        assert len(decision.failed_checks) == 1
        assert decision.failed_checks[0].name == "ci"

    def test_frozen(self) -> None:
        """RepairDecision should be immutable."""
        import pytest

        decision = RepairDecision()
        with pytest.raises(AttributeError):
            decision.repair_needed = True  # type: ignore[misc]
