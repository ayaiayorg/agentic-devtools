"""Tests for _mark_run_triggered."""

import json
from pathlib import Path

from agentic_devtools.cli.copilot.auto_start import _mark_run_triggered


def _state_file(tmp_path: Path, content: str | None = None) -> Path:
    """Create a state file with the given content and return its path."""
    state_dir = tmp_path / "state_dir"
    state_dir.mkdir(parents=True, exist_ok=True)
    sf = state_dir / "state.json"
    if content is not None:
        sf.write_text(content, encoding="utf-8")
    return sf


class TestMarkRunTriggered:
    """Tests for _mark_run_triggered helper."""

    def test_adds_run_id_and_returns_true(self, tmp_path):
        """Adds the run ID to an empty triggered list and returns True."""
        sf = _state_file(tmp_path, "{}")
        result = _mark_run_triggered(sf, "run-1")
        assert result is True
        state = json.loads(sf.read_text(encoding="utf-8"))
        assert "run-1" in state["copilot"]["auto_start_triggered_runs"]

    def test_returns_false_when_run_id_already_present(self, tmp_path):
        """Returns False (race lost) when the run ID is already in the list."""
        sf = _state_file(
            tmp_path,
            json.dumps({"copilot": {"auto_start_triggered_runs": ["run-1"]}}),
        )
        result = _mark_run_triggered(sf, "run-1")
        assert result is False

    def test_creates_nested_keys_when_absent(self, tmp_path):
        """Creates the copilot.auto_start_triggered_runs key hierarchy."""
        sf = _state_file(tmp_path, "{}")
        _mark_run_triggered(sf, "run-1")
        state = json.loads(sf.read_text(encoding="utf-8"))
        assert state["copilot"]["auto_start_triggered_runs"] == ["run-1"]

    def test_normalizes_non_dict_top_level_state(self, tmp_path):
        """Overwrites valid non-object JSON with the expected state structure."""
        sf = _state_file(tmp_path, json.dumps(["wrong-top-level"]))

        result = _mark_run_triggered(sf, "run-1")

        assert result is True
        state = json.loads(sf.read_text(encoding="utf-8"))
        assert state == {"copilot": {"auto_start_triggered_runs": ["run-1"]}}

    def test_overwrites_non_dict_copilot_namespace(self, tmp_path):
        """Replaces a non-dict copilot namespace with the expected structure."""
        sf = _state_file(tmp_path, json.dumps({"copilot": "wrong-type"}))

        result = _mark_run_triggered(sf, "run-1")

        assert result is True
        state = json.loads(sf.read_text(encoding="utf-8"))
        assert state == {"copilot": {"auto_start_triggered_runs": ["run-1"]}}

    def test_recovers_from_corrupt_json_content(self, tmp_path):
        """Treats invalid JSON as empty state and still records the run ID."""
        sf = _state_file(tmp_path, "{not-json")

        result = _mark_run_triggered(sf, "run-1")

        assert result is True
        state = json.loads(sf.read_text(encoding="utf-8"))
        assert state == {"copilot": {"auto_start_triggered_runs": ["run-1"]}}

    def test_normalizes_non_list_triggered_runs_value(self, tmp_path):
        """Replaces non-list auto_start_triggered_runs with a list before append."""
        sf = _state_file(
            tmp_path,
            json.dumps({"copilot": {"auto_start_triggered_runs": "wrong-type"}}),
        )

        result = _mark_run_triggered(sf, "run-1")

        assert result is True
        state = json.loads(sf.read_text(encoding="utf-8"))
        assert state == {"copilot": {"auto_start_triggered_runs": ["run-1"]}}
