"""Tests for is_tentative_expired."""

from agentic_devtools.cli.ci.resolution.models import ResolutionVerdict, ThreadResolutionState
from agentic_devtools.cli.ci.resolution.state_persistence import is_tentative_expired


def test_is_tentative_expired() -> None:
    state = ThreadResolutionState(
        thread_id="PRT_abc",
        verdict=ResolutionVerdict.TENTATIVE,
        tier_name="engine",
        confidence="low",
        iteration_count=5,
    )
    assert is_tentative_expired(state) is True
