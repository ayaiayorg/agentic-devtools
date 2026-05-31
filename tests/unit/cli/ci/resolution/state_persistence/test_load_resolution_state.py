"""Tests for load_resolution_state."""

from pathlib import Path

from agentic_devtools.cli.ci.resolution.state_persistence import _thread_id_to_filename, load_resolution_state


def test_load_nonexistent_returns_none(tmp_path: Path) -> None:
    result = load_resolution_state("nonexistent", tmp_path)
    assert result is None


def test_load_corrupt_file_returns_none(tmp_path: Path) -> None:
    safe_id = _thread_id_to_filename("PRT_corrupt")
    file_path = tmp_path / f"{safe_id}.json"
    file_path.write_text("not json")
    result = load_resolution_state("PRT_corrupt", tmp_path)
    assert result is None
