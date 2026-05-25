"""Tests for ActionResult dataclass."""

from agentic_devtools.cli.ci.pipeline.models import ActionDecision, ActionResult


class TestActionResult:
    """Tests for ActionResult construction and fields."""

    def test_default_construction(self) -> None:
        result = ActionResult(name="test", decision=ActionDecision.SKIP)
        assert result.name == "test"
        assert result.decision == ActionDecision.SKIP
        assert result.preconditions == {}
        assert result.details == ""
        assert result.error == ""

    def test_full_construction(self) -> None:
        result = ActionResult(
            name="guards",
            decision=ActionDecision.BLOCKED,
            preconditions={"not_fork": False},
            details="PR is from a fork",
            error="",
        )
        assert result.name == "guards"
        assert result.decision == ActionDecision.BLOCKED
        assert result.preconditions == {"not_fork": False}
        assert result.details == "PR is from a fork"

    def test_with_error(self) -> None:
        result = ActionResult(
            name="merge",
            decision=ActionDecision.FAILED,
            error="API timeout",
        )
        assert result.error == "API timeout"
