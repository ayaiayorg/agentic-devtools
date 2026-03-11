"""Tests for agentic_devtools.state.clear_state."""

from agentic_devtools import state


def test_clear_state(temp_state_dir):
    """Test clearing all state writes an empty JSON file."""
    state.set_value("key1", "value1")
    state.set_value("key2", "value2")
    state.clear_state()
    assert state.load_state() == {}


def test_clear_state_preserves_state_directory(temp_state_dir):
    """Test that clear_state does not delete the state directory."""
    state.set_value("key1", "value1")
    state.clear_state()
    assert temp_state_dir.exists()


def test_clear_state_preserves_subdirectories(temp_state_dir):
    """Test that clear_state does not delete subdirectories in state dir."""
    subdir = temp_state_dir / "workflows"
    subdir.mkdir()
    (subdir / "artifact.json").write_text('{"key": "value"}', encoding="utf-8")

    state.set_value("key1", "value1")
    state.clear_state()

    assert state.load_state() == {}
    assert subdir.exists()
    assert (subdir / "artifact.json").exists()


def test_clear_state_preserves_other_files(temp_state_dir):
    """Test that clear_state does not delete other files in state dir."""
    other_file = temp_state_dir / "temp-data.json"
    other_file.write_text("{}", encoding="utf-8")

    state.set_value("key1", "value1")
    state.clear_state()

    assert state.load_state() == {}
    assert other_file.exists()
