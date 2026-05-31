"""Tests for clear_resolution_state."""

from pathlib import Path
from unittest.mock import patch

from agentic_devtools.cli.ci.resolution.models import ResolutionVerdict, ThreadResolutionState
from agentic_devtools.cli.ci.resolution.state_persistence import (
    clear_resolution_state,
    load_resolution_state,
    save_resolution_state,
)


def test_clear_resolution_state_removes_file(tmp_path: Path) -> None:
    state = ThreadResolutionState(
        thread_id="PRT_abc",
        verdict=ResolutionVerdict.TENTATIVE,
        tier_name="engine",
        confidence="low",
    )
    save_resolution_state(state, tmp_path)
    clear_resolution_state("PRT_abc", tmp_path)
    assert load_resolution_state("PRT_abc", tmp_path) is None


def test_clear_resolution_state_nonexistent_is_noop(tmp_path: Path) -> None:
    clear_resolution_state("nonexistent_thread", tmp_path)


def test_clear_resolution_state_oserror_is_logged(tmp_path: Path) -> None:
    state = ThreadResolutionState(
        thread_id="PRT_abc",
        verdict=ResolutionVerdict.TENTATIVE,
        tier_name="engine",
        confidence="low",
    )
    save_resolution_state(state, tmp_path)
    with patch.object(Path, "unlink", side_effect=OSError("permission denied")):
        clear_resolution_state("PRT_abc", tmp_path)
