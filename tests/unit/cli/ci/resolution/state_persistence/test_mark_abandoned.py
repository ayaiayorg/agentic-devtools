"""Tests for mark_abandoned."""

from pathlib import Path

from agentic_devtools.cli.ci.resolution.models import ResolutionVerdict, ThreadResolutionState
from agentic_devtools.cli.ci.resolution.state_persistence import (
    load_resolution_state,
    mark_abandoned,
    save_resolution_state,
)


def test_mark_abandoned_persists_abandoned_verdict(tmp_path: Path) -> None:
    state = ThreadResolutionState(
        thread_id="PRT_abc",
        verdict=ResolutionVerdict.TENTATIVE,
        tier_name="engine",
        confidence="low",
        iteration_count=4,
    )
    save_resolution_state(state, tmp_path)
    mark_abandoned("PRT_abc", tmp_path)
    loaded = load_resolution_state("PRT_abc", tmp_path)
    assert loaded is not None
    assert loaded.verdict == ResolutionVerdict.ABANDONED
    assert loaded.iteration_count == 4


def test_mark_abandoned_nonexistent_file_is_noop(tmp_path: Path) -> None:
    mark_abandoned("nonexistent_thread", tmp_path)
    assert load_resolution_state("nonexistent_thread", tmp_path) is None
