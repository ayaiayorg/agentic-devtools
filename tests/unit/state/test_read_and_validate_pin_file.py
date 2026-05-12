"""Tests for agentic_devtools.state.read_and_validate_pin_file."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from agentic_devtools import state
from agentic_devtools.state import (
    PIN_FILENAME,
    read_and_validate_pin_file,
)


@pytest.fixture(autouse=True)
def _reset_pin_logged():
    """Reset the _pin_logged flag between tests."""
    state._pin_logged = False
    yield
    state._pin_logged = False


class TestReadAndValidatePinFile:
    """Tests for read_and_validate_pin_file function."""

    def _write_pin(self, git_root, state_dir, workflow="pull-request-review", ttl_hours=24, created_utc=None):
        """Helper to write a pin file."""
        agdt_dir = git_root / ".agdt"
        agdt_dir.mkdir(parents=True, exist_ok=True)
        if created_utc is None:
            created_utc = datetime.now(timezone.utc).isoformat()
        data = {
            "state_dir": str(state_dir),
            "workflow": workflow,
            "created_utc": created_utc,
            "ttl_hours": ttl_hours,
        }
        (agdt_dir / PIN_FILENAME).write_text(json.dumps(data), encoding="utf-8")

    def test_valid_pin_honored(self, tmp_path):
        """Valid pin file returns the state directory path."""
        state_dir = tmp_path / ".agdt" / "workflows" / "user" / "PROJ-123"
        state_dir.mkdir(parents=True)
        self._write_pin(tmp_path, state_dir)

        result = read_and_validate_pin_file(tmp_path)
        assert result == state_dir.resolve()

    def test_missing_pin_file_returns_none(self, tmp_path):
        """Missing pin file returns None."""
        result = read_and_validate_pin_file(tmp_path)
        assert result is None

    def test_invalid_json_ignored(self, tmp_path, capsys):
        """Invalid JSON pin file is ignored with diagnostic."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        (agdt_dir / PIN_FILENAME).write_text("not json{{{", encoding="utf-8")

        result = read_and_validate_pin_file(tmp_path)
        assert result is None
        captured = capsys.readouterr()
        assert "[agdt]" in captured.err

    def test_missing_fields_ignored(self, tmp_path, capsys):
        """Pin file with missing required fields is ignored."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        (agdt_dir / PIN_FILENAME).write_text(json.dumps({"state_dir": "/tmp"}), encoding="utf-8")

        result = read_and_validate_pin_file(tmp_path)
        assert result is None
        captured = capsys.readouterr()
        assert "[agdt]" in captured.err

    def test_empty_string_fields_ignored(self, tmp_path, capsys):
        """Pin file with empty string fields (present but empty) is ignored."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        data = {
            "state_dir": "",
            "workflow": "pull-request-review",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "ttl_hours": 24,
        }
        (agdt_dir / PIN_FILENAME).write_text(json.dumps(data), encoding="utf-8")

        result = read_and_validate_pin_file(tmp_path)
        assert result is None
        captured = capsys.readouterr()
        assert "empty required string fields" in captured.err

    def test_unrecognized_workflow_ignored(self, tmp_path, capsys):
        """Pin with unrecognized workflow is ignored."""
        state_dir = tmp_path / ".agdt" / "workflows" / "user" / "KEY-1"
        state_dir.mkdir(parents=True)
        self._write_pin(tmp_path, state_dir, workflow="unknown-workflow")

        result = read_and_validate_pin_file(tmp_path)
        assert result is None
        captured = capsys.readouterr()
        assert "[agdt]" in captured.err

    def test_relative_state_dir_rejected(self, tmp_path, capsys):
        """Relative state_dir is rejected."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        data = {
            "state_dir": "relative/path",
            "workflow": "pull-request-review",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "ttl_hours": 24,
        }
        (agdt_dir / PIN_FILENAME).write_text(json.dumps(data), encoding="utf-8")

        result = read_and_validate_pin_file(tmp_path)
        assert result is None
        captured = capsys.readouterr()
        assert "[agdt]" in captured.err

    def test_state_dir_outside_repo_root_rejected(self, tmp_path, capsys):
        """state_dir outside repo root is rejected."""
        # Use an absolute path outside tmp_path that works cross-platform
        outside_dir = tmp_path.parent / "outside_repo_for_test"
        self._write_pin(tmp_path, outside_dir)

        result = read_and_validate_pin_file(tmp_path)
        assert result is None
        captured = capsys.readouterr()
        assert "[agdt]" in captured.err

    def test_state_dir_inside_repo_but_outside_workflows_rejected(self, tmp_path, capsys):
        """state_dir inside repo root but outside .agdt/workflows/ is rejected."""
        # Path is under repo root but not under .agdt/workflows/
        inside_repo_dir = tmp_path / "src"
        inside_repo_dir.mkdir(parents=True)
        self._write_pin(tmp_path, inside_repo_dir)

        result = read_and_validate_pin_file(tmp_path)
        assert result is None
        captured = capsys.readouterr()
        assert ".agdt/workflows/" in captured.err

    def test_state_dir_under_agdt_but_not_workflows_rejected(self, tmp_path, capsys):
        """state_dir under .agdt/ but not .agdt/workflows/ is rejected."""
        # Path is under .agdt/ directly but not under .agdt/workflows/
        agdt_other_dir = tmp_path / ".agdt" / "other"
        agdt_other_dir.mkdir(parents=True)
        self._write_pin(tmp_path, agdt_other_dir)

        result = read_and_validate_pin_file(tmp_path)
        assert result is None
        captured = capsys.readouterr()
        assert ".agdt/workflows/" in captured.err

    def test_expired_ttl_ignored(self, tmp_path, capsys):
        """Expired TTL pin is ignored with diagnostic."""
        state_dir = tmp_path / ".agdt" / "workflows" / "user" / "PROJ-1"
        state_dir.mkdir(parents=True)
        expired = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        self._write_pin(tmp_path, state_dir, created_utc=expired, ttl_hours=24)

        result = read_and_validate_pin_file(tmp_path)
        assert result is None
        captured = capsys.readouterr()
        assert "expired" in captured.err.lower()

    def test_non_existent_uncreatable_path_rejected(self, tmp_path, capsys):
        """state_dir that cannot be created is rejected."""
        # Use a path inside tmp_path (so it passes the containment check)
        # and monkeypatch Path.mkdir to raise OSError for cross-platform reliability.
        uncreatable = tmp_path / ".agdt" / "workflows" / "user" / "UNCREATABLE"
        self._write_pin(tmp_path, uncreatable)

        with patch.object(Path, "mkdir", side_effect=OSError("mock mkdir failure")):
            result = read_and_validate_pin_file(tmp_path)
        assert result is None
        captured = capsys.readouterr()
        assert "[agdt]" in captured.err

    def test_non_existent_but_creatable_path_succeeds(self, tmp_path):
        """state_dir that doesn't exist but can be created succeeds."""
        state_dir = tmp_path / ".agdt" / "workflows" / "user" / "NEW-DIR"
        # Don't create it - let read_and_validate_pin_file create it
        self._write_pin(tmp_path, state_dir)

        result = read_and_validate_pin_file(tmp_path)
        assert result == state_dir.resolve()
        assert state_dir.exists()

    def test_not_a_dict_ignored(self, tmp_path, capsys):
        """Pin file that is not a JSON object is ignored."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        (agdt_dir / PIN_FILENAME).write_text(json.dumps([1, 2, 3]), encoding="utf-8")

        result = read_and_validate_pin_file(tmp_path)
        assert result is None
        captured = capsys.readouterr()
        assert "[agdt]" in captured.err

    def test_invalid_created_utc_ignored(self, tmp_path, capsys):
        """Invalid created_utc timestamp is ignored."""
        state_dir = tmp_path / ".agdt" / "workflows" / "user" / "KEY-1"
        state_dir.mkdir(parents=True)
        self._write_pin(tmp_path, state_dir, created_utc="not-a-timestamp")

        result = read_and_validate_pin_file(tmp_path)
        assert result is None
        captured = capsys.readouterr()
        assert "[agdt]" in captured.err

    def test_oserror_on_read_returns_none(self, tmp_path):
        """Returns None if reading the pin file raises OSError."""
        self._write_pin(tmp_path, "/some/path")
        with patch("pathlib.Path.read_text", side_effect=OSError("mock read error")):
            result = read_and_validate_pin_file(tmp_path)
        assert result is None

    def test_naive_timestamp_gets_tzinfo(self, tmp_path):
        """Naive timestamp gets tzinfo UTC applied."""
        import datetime

        from agentic_devtools.state import read_and_validate_pin_file
        state_dir = tmp_path / ".agdt" / "workflows" / "user" / "KEY-1"
        state_dir.mkdir(parents=True)
        # Create a naive timestamp
        created_utc = datetime.datetime.now().isoformat()
        self._write_pin(tmp_path, state_dir, created_utc=created_utc)

        result = read_and_validate_pin_file(tmp_path)
        assert result == state_dir.resolve()

    def test_oserror_on_mkdir_returns_none(self, tmp_path):
        """Returns None if state_dir_path.mkdir raises OSError."""
        state_dir = tmp_path / ".agdt" / "workflows" / "user" / "KEY-1"
        self._write_pin(tmp_path, state_dir)
        with patch("pathlib.Path.mkdir", side_effect=OSError("mock mkdir error")):
            result = read_and_validate_pin_file(tmp_path)
        assert result is None

    def test_invalid_ttl_hours_string_rejected(self, tmp_path, capsys):
        """String ttl_hours is rejected with specific diagnostic."""
        state_dir = tmp_path / ".agdt" / "workflows" / "user" / "KEY-1"
        state_dir.mkdir(parents=True)
        self._write_pin(tmp_path, state_dir, ttl_hours="not-a-number")

        result = read_and_validate_pin_file(tmp_path)
        assert result is None
        captured = capsys.readouterr()
        assert "invalid ttl_hours" in captured.err

    def test_negative_ttl_hours_rejected(self, tmp_path, capsys):
        """Negative ttl_hours is rejected."""
        state_dir = tmp_path / ".agdt" / "workflows" / "user" / "KEY-2"
        state_dir.mkdir(parents=True)
        self._write_pin(tmp_path, state_dir, ttl_hours=-5)

        result = read_and_validate_pin_file(tmp_path)
        assert result is None
        captured = capsys.readouterr()
        assert "invalid ttl_hours" in captured.err

    def test_zero_ttl_hours_rejected(self, tmp_path, capsys):
        """Zero ttl_hours is rejected."""
        state_dir = tmp_path / ".agdt" / "workflows" / "user" / "KEY-3"
        state_dir.mkdir(parents=True)
        self._write_pin(tmp_path, state_dir, ttl_hours=0)

        result = read_and_validate_pin_file(tmp_path)
        assert result is None
        captured = capsys.readouterr()
        # ttl_hours=0 passes the None check but fails the dedicated ttl validation
        assert "invalid ttl_hours" in captured.err

    def test_boolean_ttl_hours_rejected(self, tmp_path, capsys):
        """Boolean ttl_hours is rejected."""
        state_dir = tmp_path / ".agdt" / "workflows" / "user" / "KEY-4"
        state_dir.mkdir(parents=True)
        self._write_pin(tmp_path, state_dir, ttl_hours=True)

        result = read_and_validate_pin_file(tmp_path)
        assert result is None
        captured = capsys.readouterr()
        assert "[agdt]" in captured.err
