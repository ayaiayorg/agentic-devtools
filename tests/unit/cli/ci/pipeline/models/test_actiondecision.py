"""Tests for ActionDecision enum."""

from agentic_devtools.cli.ci.pipeline.models import ActionDecision


class TestActionDecision:
    """Tests for the ActionDecision enum values."""

    def test_has_execute_value(self) -> None:
        assert ActionDecision.EXECUTE.value == "execute"

    def test_has_skip_value(self) -> None:
        assert ActionDecision.SKIP.value == "skip"

    def test_has_blocked_value(self) -> None:
        assert ActionDecision.BLOCKED.value == "blocked"

    def test_has_blocked_by_guard_value(self) -> None:
        assert ActionDecision.BLOCKED_BY_GUARD.value == "blocked_by_guard"

    def test_has_failed_value(self) -> None:
        assert ActionDecision.FAILED.value == "failed"

    def test_all_members_present(self) -> None:
        members = {m.name for m in ActionDecision}
        assert members == {"EXECUTE", "SKIP", "BLOCKED", "BLOCKED_BY_GUARD", "FAILED"}
