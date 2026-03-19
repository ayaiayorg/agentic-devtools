"""Tests for _unmark_run_triggered."""

import json
from pathlib import Path

import agentic_devtools.cli.copilot.auto_start as auto_start_module
from agentic_devtools.cli.copilot.auto_start import _unmark_run_triggered


def _state_file(tmp_path: Path, content: str | None = None) -> Path:
    """Create a state file with the given content and return its path."""
    state_dir = tmp_path / "state_dir"
    state_dir.mkdir(parents=True, exist_ok=True)
    sf = state_dir / "state.json"
    if content is not None:
        sf.write_text(content, encoding="utf-8")
    return sf


class TestUnmarkRunTriggered:
    """Tests for _unmark_run_triggered helper."""

    def test_removes_run_id_from_triggered_list(self, tmp_path):
        """Removes the run ID from the triggered list."""
        sf = _state_file(
            tmp_path,
            json.dumps({"copilot": {"auto_start_triggered_runs": ["run-1", "run-2"]}}),
        )
        _unmark_run_triggered(sf, "run-1")
        state = json.loads(sf.read_text(encoding="utf-8"))
        assert state["copilot"]["auto_start_triggered_runs"] == ["run-2"]

    def test_silently_ignores_missing_run_id(self, tmp_path):
        """Does nothing when the run ID is not in the list."""
        sf = _state_file(
            tmp_path,
            json.dumps({"copilot": {"auto_start_triggered_runs": ["other"]}}),
        )
        _unmark_run_triggered(sf, "run-1")
        state = json.loads(sf.read_text(encoding="utf-8"))
        assert state["copilot"]["auto_start_triggered_runs"] == ["other"]

    def test_silently_ignores_corrupt_json(self, tmp_path):
        """Does not raise when the state file contains invalid JSON."""
        sf = _state_file(tmp_path, "{not valid json!!!")
        _unmark_run_triggered(sf, "run-1")  # Should not raise

    def test_silently_ignores_missing_state_file(self, tmp_path):
        """Does not raise when the state file does not exist."""
        sf = tmp_path / "nonexistent" / "state.json"
        _unmark_run_triggered(sf, "run-1")  # Should not raise

    def test_handles_non_dict_top_level_state(self, tmp_path):
        """Treats a non-dict top-level JSON value as empty state."""
        sf = _state_file(tmp_path, json.dumps(["unexpected", "state"]))

        _unmark_run_triggered(sf, "run-1")

        assert json.loads(sf.read_text(encoding="utf-8")) == ["unexpected", "state"]

    def test_handles_non_dict_copilot_value(self, tmp_path):
        """Normalizes non-dict copilot state without raising."""
        sf = _state_file(
            tmp_path,
            json.dumps({"copilot": "unexpected", "other": {"k": "v"}}),
        )

        _unmark_run_triggered(sf, "run-1")

        # No run was removed, so the helper should not rewrite the file.
        state = json.loads(sf.read_text(encoding="utf-8"))
        assert state["copilot"] == "unexpected"
        assert state["other"] == {"k": "v"}

    def test_handles_non_list_triggered_value(self, tmp_path):
        """Normalizes non-list triggered-runs value without raising."""
        sf = _state_file(
            tmp_path,
            json.dumps({"copilot": {"auto_start_triggered_runs": "run-1"}}),
        )

        _unmark_run_triggered(sf, "run-1")

        # No run was removed, so the helper should not rewrite the file.
        state = json.loads(sf.read_text(encoding="utf-8"))
        assert state["copilot"]["auto_start_triggered_runs"] == "run-1"

    def test_silently_ignores_locking_errors(self, tmp_path, monkeypatch):
        """Swallows exceptions raised while trying to lock/read state."""
        sf = _state_file(
            tmp_path,
            json.dumps({"copilot": {"auto_start_triggered_runs": ["run-1"]}}),
        )

        def _raise_lock_error(_state_file_path):
            raise OSError("lock failed")

        monkeypatch.setattr(auto_start_module, "locked_state_file", _raise_lock_error)

        _unmark_run_triggered(sf, "run-1")  # Should not raise
