"""Tests for increment_iteration."""

from pathlib import Path

from agentic_devtools.cli.ci.resolution.models import ResolutionVerdict, ThreadResolutionState
from agentic_devtools.cli.ci.resolution.state_persistence import increment_iteration, load_resolution_state


def test_increment_iteration(tmp_path: Path) -> None:
    state = ThreadResolutionState(
        thread_id="PRT_abc",
        verdict=ResolutionVerdict.TENTATIVE,
        tier_name="engine",
        confidence="low",
        iteration_count=2,
    )
    updated = increment_iteration(state, tmp_path)
    assert updated.iteration_count == 3
    loaded = load_resolution_state("PRT_abc", tmp_path)
    assert loaded is not None
    assert loaded.iteration_count == 3
