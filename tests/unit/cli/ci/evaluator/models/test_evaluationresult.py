"""Tests for EvaluationResult dataclass."""

from agentic_devtools.cli.ci.evaluator.models import (
    EvaluationResult,
    PostAgentAction,
    PostAgentClassification,
)


class TestEvaluationResult:
    """Tests for EvaluationResult frozen dataclass."""

    def test_default_values(self):
        """EvaluationResult has sensible defaults."""
        r = EvaluationResult(
            classification=PostAgentClassification.complete,
            action_taken=PostAgentAction.no_action,
        )
        assert r.success is True
        assert r.threads_resolved == 0
        assert r.threads_unresolved == 0
        assert r.error_details is None
        assert r.dry_run is False

    def test_to_dict(self):
        """to_dict serializes all fields."""
        r = EvaluationResult(
            classification=PostAgentClassification.agent_silent,
            action_taken=PostAgentAction.agentic_fallback,
            success=False,
            threads_resolved=2,
            threads_unresolved=3,
            error_details="API error",
            dry_run=True,
        )
        d = r.to_dict()
        assert d["classification"] == "agent_silent"
        assert d["action_taken"] == "agentic_fallback"
        assert d["success"] is False
        assert d["threads_resolved"] == 2
        assert d["threads_unresolved"] == 3
        assert d["error_details"] == "API error"
        assert d["dry_run"] is True

    def test_frozen(self):
        """EvaluationResult is immutable."""
        r = EvaluationResult(
            classification=PostAgentClassification.complete,
            action_taken=PostAgentAction.no_action,
        )
        try:
            r.success = False  # type: ignore[misc]
            assert False, "Should raise"
        except AttributeError:
            pass
