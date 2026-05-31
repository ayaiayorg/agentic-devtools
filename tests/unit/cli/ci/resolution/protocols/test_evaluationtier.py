"""Tests for EvaluationTier protocol."""

from agentic_devtools.cli.ci.resolution.models import TierResult
from agentic_devtools.cli.ci.resolution.protocols import EvaluationTier


class MockTier:
    @property
    def name(self) -> str:
        return "mock_tier"

    def evaluate(self, thread, context) -> TierResult | None:
        return None


def test_evaluation_tier_protocol() -> None:
    tier = MockTier()
    assert isinstance(tier, EvaluationTier)
