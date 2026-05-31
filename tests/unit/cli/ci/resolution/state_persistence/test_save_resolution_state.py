"""Tests for save_resolution_state."""

from pathlib import Path
from unittest.mock import patch

from agentic_devtools.cli.ci.resolution.models import ResolutionVerdict, ThreadResolutionState
from agentic_devtools.cli.ci.resolution.state_persistence import load_resolution_state, save_resolution_state


def test_save_and_load(tmp_path: Path) -> None:
    state = ThreadResolutionState(
        thread_id="PRT_abc",
        verdict=ResolutionVerdict.TENTATIVE,
        tier_name="engine",
        confidence="low",
        timestamp="2026-01-01T00:00:00+00:00",
        iteration_count=2,
    )
    save_resolution_state(state, tmp_path)
    loaded = load_resolution_state("PRT_abc", tmp_path)
    assert loaded is not None
    assert loaded.thread_id == "PRT_abc"


def test_save_oserror_is_logged(tmp_path: Path) -> None:
    state = ThreadResolutionState(
        thread_id="PRT_abc",
        verdict=ResolutionVerdict.TENTATIVE,
        tier_name="engine",
        confidence="low",
    )
    with patch.object(Path, "write_text", side_effect=OSError("disk full")):
        save_resolution_state(state, tmp_path)
    assert load_resolution_state("PRT_abc", tmp_path) is None
