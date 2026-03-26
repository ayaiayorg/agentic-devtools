"""Tests for _read_model_from_state."""

import json
from pathlib import Path

from agentic_devtools.cli.copilot.auto_start import _read_model_from_state


def _write_state(path: Path, state: dict) -> None:
    """Write a state dict to the given path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state), encoding="utf-8")


class TestReadModelFromState:
    """Tests for _read_model_from_state helper."""

    def test_returns_model_when_present(self, tmp_path):
        """Returns the model_id string when present in state."""
        state_file = tmp_path / "state.json"
        _write_state(state_file, {"copilot": {"model_id": "gemini-pro-3.1"}})

        result = _read_model_from_state(state_file)

        assert result == "gemini-pro-3.1"

    def test_returns_none_when_key_missing(self, tmp_path):
        """Returns None when copilot.model_id is not in state."""
        state_file = tmp_path / "state.json"
        _write_state(state_file, {"copilot": {}})

        result = _read_model_from_state(state_file)

        assert result is None

    def test_returns_none_when_copilot_ns_missing(self, tmp_path):
        """Returns None when the copilot namespace is missing."""
        state_file = tmp_path / "state.json"
        _write_state(state_file, {"other": "data"})

        result = _read_model_from_state(state_file)

        assert result is None

    def test_returns_none_when_model_is_empty_string(self, tmp_path):
        """Returns None when model_id is an empty string."""
        state_file = tmp_path / "state.json"
        _write_state(state_file, {"copilot": {"model_id": ""}})

        result = _read_model_from_state(state_file)

        assert result is None

    def test_returns_none_when_model_is_whitespace_only(self, tmp_path):
        """Returns None when model_id is whitespace-only."""
        state_file = tmp_path / "state.json"
        _write_state(state_file, {"copilot": {"model_id": "   "}})

        result = _read_model_from_state(state_file)

        assert result is None

    def test_strips_whitespace_from_model(self, tmp_path):
        """Strips leading/trailing whitespace from model_id."""
        state_file = tmp_path / "state.json"
        _write_state(state_file, {"copilot": {"model_id": "  gpt-4  "}})

        result = _read_model_from_state(state_file)

        assert result == "gpt-4"

    def test_returns_none_when_model_is_not_string(self, tmp_path):
        """Returns None when model_id is not a string."""
        state_file = tmp_path / "state.json"
        _write_state(state_file, {"copilot": {"model_id": 42}})

        result = _read_model_from_state(state_file)

        assert result is None

    def test_returns_none_when_file_does_not_exist(self, tmp_path):
        """Returns None when the state file does not exist."""
        state_file = tmp_path / "nonexistent.json"

        result = _read_model_from_state(state_file)

        assert result is None

    def test_returns_none_when_file_is_empty(self, tmp_path):
        """Returns None when the state file is empty."""
        state_file = tmp_path / "state.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text("", encoding="utf-8")

        result = _read_model_from_state(state_file)

        assert result is None

    def test_returns_none_when_json_malformed(self, tmp_path):
        """Returns None when the state file contains invalid JSON."""
        state_file = tmp_path / "state.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text("{invalid json", encoding="utf-8")

        result = _read_model_from_state(state_file)

        assert result is None

    def test_returns_none_when_state_is_not_dict(self, tmp_path):
        """Returns None when the top-level state is not a dict."""
        state_file = tmp_path / "state.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text("[1, 2, 3]", encoding="utf-8")

        result = _read_model_from_state(state_file)

        assert result is None

    def test_returns_none_when_copilot_is_not_dict(self, tmp_path):
        """Returns None when the copilot key is not a dict."""
        state_file = tmp_path / "state.json"
        _write_state(state_file, {"copilot": "not-a-dict"})

        result = _read_model_from_state(state_file)

        assert result is None
