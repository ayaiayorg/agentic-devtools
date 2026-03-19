"""Tests for _is_run_triggered."""

import json
from pathlib import Path

from agentic_devtools.cli.copilot.auto_start import _is_run_triggered


def _state_file(tmp_path: Path, content: str | None = None) -> Path:
    """Create a state file with the given content and return its path."""
    state_dir = tmp_path / "state_dir"
    state_dir.mkdir(parents=True, exist_ok=True)
    sf = state_dir / "state.json"
    if content is not None:
        sf.write_text(content, encoding="utf-8")
    return sf


class TestIsRunTriggered:
    """Tests for _is_run_triggered helper."""

    def test_returns_true_when_run_id_present(self, tmp_path):
        """Returns True when the run ID is in the triggered list."""
        sf = _state_file(
            tmp_path,
            json.dumps({"copilot": {"auto_start_triggered_runs": ["run-1"]}}),
        )
        assert _is_run_triggered(sf, "run-1") is True

    def test_returns_false_when_run_id_absent(self, tmp_path):
        """Returns False when the run ID is not in the triggered list."""
        sf = _state_file(
            tmp_path,
            json.dumps({"copilot": {"auto_start_triggered_runs": ["other"]}}),
        )
        assert _is_run_triggered(sf, "run-1") is False

    def test_returns_false_when_state_file_missing(self, tmp_path):
        """Returns False (not raises) when the state file does not exist."""
        sf = tmp_path / "nonexistent" / "state.json"
        assert _is_run_triggered(sf, "run-1") is False

    def test_returns_false_when_json_is_corrupt(self, tmp_path):
        """Returns False when the state file contains invalid JSON."""
        sf = _state_file(tmp_path, "{not valid json!!!")
        assert _is_run_triggered(sf, "run-1") is False

    def test_returns_false_when_triggered_is_not_a_list(self, tmp_path):
        """Returns False when auto_start_triggered_runs is not a list."""
        sf = _state_file(
            tmp_path,
            json.dumps({"copilot": {"auto_start_triggered_runs": "not-a-list"}}),
        )
        assert _is_run_triggered(sf, "run-1") is False

    def test_returns_false_when_state_json_is_not_an_object(self, tmp_path):
        """Returns False when state.json contains valid non-object JSON."""
        sf = _state_file(tmp_path, json.dumps(["not", "an", "object"]))
        assert _is_run_triggered(sf, "run-1") is False

    def test_returns_false_when_copilot_namespace_is_not_an_object(self, tmp_path):
        """Returns False when the copilot namespace is a non-dict JSON value."""
        sf = _state_file(tmp_path, json.dumps({"copilot": ["wrong-type"]}))
        assert _is_run_triggered(sf, "run-1") is False
