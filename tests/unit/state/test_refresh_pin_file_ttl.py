"""Tests for agentic_devtools.state.refresh_pin_file_ttl."""

import json
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from agentic_devtools.state import PIN_FILENAME, refresh_pin_file_ttl


class TestRefreshPinFileTtl:
    """Tests for refresh_pin_file_ttl function."""

    def _write_pin(self, git_root, created_utc=None):
        """Helper to write a valid pin file."""
        agdt_dir = git_root / ".agdt"
        agdt_dir.mkdir(parents=True, exist_ok=True)
        state_dir = git_root / ".agdt" / "workflows" / "user" / "PROJ-1"
        state_dir.mkdir(parents=True, exist_ok=True)
        if created_utc is None:
            created_utc = "2020-01-01T00:00:00+00:00"  # old timestamp
        data = {
            "state_dir": str(state_dir),
            "workflow": "pull-request-review",
            "created_utc": created_utc,
            "ttl_hours": 24,
        }
        pin_path = agdt_dir / PIN_FILENAME
        pin_path.write_text(json.dumps(data), encoding="utf-8")
        return pin_path

    def test_refreshes_created_utc(self, tmp_path):
        """Existing valid pin has created_utc refreshed to now."""
        pin_path = self._write_pin(tmp_path)

        with patch("agentic_devtools.state._get_git_repo_root", return_value=tmp_path):
            refresh_pin_file_ttl()

        data = json.loads(pin_path.read_text(encoding="utf-8"))
        refreshed = datetime.fromisoformat(data["created_utc"])
        # Should be very recent (within last 5 seconds)
        now = datetime.now(timezone.utc)
        assert (now - refreshed).total_seconds() < 5

    def test_noop_when_pin_absent(self, tmp_path):
        """No-op when pin file doesn't exist."""
        (tmp_path / ".agdt").mkdir()
        with patch("agentic_devtools.state._get_git_repo_root", return_value=tmp_path):
            # Should not raise
            refresh_pin_file_ttl()

    def test_noop_when_not_in_git_repo(self):
        """No-op when not in a git repo."""
        with patch("agentic_devtools.state._get_git_repo_root", return_value=None):
            # Should not raise
            refresh_pin_file_ttl()

    def test_noop_when_invalid_json(self, tmp_path):
        """No-op when pin file contains invalid JSON."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        pin_path = agdt_dir / PIN_FILENAME
        pin_path.write_text("not json", encoding="utf-8")

        with patch("agentic_devtools.state._get_git_repo_root", return_value=tmp_path):
            refresh_pin_file_ttl()

        # File should remain unchanged
        assert pin_path.read_text(encoding="utf-8") == "not json"

    def test_noop_when_missing_required_fields(self, tmp_path):
        """No-op when pin file is missing required fields."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        pin_path = agdt_dir / PIN_FILENAME
        pin_path.write_text(json.dumps({"state_dir": "/tmp"}), encoding="utf-8")

        with patch("agentic_devtools.state._get_git_repo_root", return_value=tmp_path):
            refresh_pin_file_ttl()

        # File should remain unchanged
        data = json.loads(pin_path.read_text(encoding="utf-8"))
        assert "created_utc" not in data or data.get("created_utc") is None

    def test_preserves_other_fields(self, tmp_path):
        """Refresh only updates created_utc, preserving other fields."""
        pin_path = self._write_pin(tmp_path)
        original_data = json.loads(pin_path.read_text(encoding="utf-8"))

        with patch("agentic_devtools.state._get_git_repo_root", return_value=tmp_path):
            refresh_pin_file_ttl()

        data = json.loads(pin_path.read_text(encoding="utf-8"))
        assert data["state_dir"] == original_data["state_dir"]
        assert data["workflow"] == original_data["workflow"]
        assert data["ttl_hours"] == original_data["ttl_hours"]
        # created_utc should be different (refreshed)
        assert data["created_utc"] != original_data["created_utc"]

    def test_ignores_non_dict_content(self, tmp_path):
        """Refresh ignores content that parses to a list instead of a dict."""
        pin_path = tmp_path / ".agdt" / PIN_FILENAME
        pin_path.parent.mkdir()
        pin_path.write_text(json.dumps(["not a dict"]), encoding="utf-8")

        with patch("agentic_devtools.state._get_git_repo_root", return_value=tmp_path):
            refresh_pin_file_ttl()

        assert pin_path.read_text(encoding="utf-8") == json.dumps(["not a dict"])

    def test_cleans_up_temp_file_on_exception(self, tmp_path):
        """Cleans up the temporary file if os.replace fails during refresh."""
        self._write_pin(tmp_path)
        agdt_dir = tmp_path / ".agdt"

        with patch("agentic_devtools.state._get_git_repo_root", return_value=tmp_path):
            with patch("os.replace", side_effect=Exception("mock replace error")):
                with pytest.raises(Exception, match="mock replace error"):
                    refresh_pin_file_ttl()

        # tmp file should be cleaned up
        assert not any(f.suffix == ".tmp" for f in agdt_dir.iterdir() if f.is_file())

    def test_ignores_oserror_during_cleanup(self, tmp_path):
        """Ignores OSError during cleanup if os.replace fails."""
        self._write_pin(tmp_path)

        with patch("agentic_devtools.state._get_git_repo_root", return_value=tmp_path):
            with patch("os.replace", side_effect=Exception("mock replace error")):
                with patch("os.unlink", side_effect=OSError("mock unlink error")):
                    with pytest.raises(Exception, match="mock replace error"):
                        refresh_pin_file_ttl()

    def test_noop_when_workflow_not_recognized(self, tmp_path):
        """No-op when workflow is not in RECOGNIZED_PIN_WORKFLOWS."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir(parents=True, exist_ok=True)
        state_dir = tmp_path / ".agdt" / "workflows" / "user" / "PROJ-1"
        state_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "state_dir": str(state_dir),
            "workflow": "unknown-workflow",
            "created_utc": "2020-01-01T00:00:00+00:00",
            "ttl_hours": 24,
        }
        pin_path = agdt_dir / PIN_FILENAME
        pin_path.write_text(json.dumps(data), encoding="utf-8")

        with patch("agentic_devtools.state._get_git_repo_root", return_value=tmp_path):
            refresh_pin_file_ttl()

        # File should remain unchanged (created_utc not refreshed)
        result = json.loads(pin_path.read_text(encoding="utf-8"))
        assert result["created_utc"] == "2020-01-01T00:00:00+00:00"

    def test_noop_when_ttl_hours_not_numeric(self, tmp_path):
        """No-op when ttl_hours is not a number."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir(parents=True, exist_ok=True)
        state_dir = tmp_path / ".agdt" / "workflows" / "user" / "PROJ-1"
        state_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "state_dir": str(state_dir),
            "workflow": "pull-request-review",
            "created_utc": "2020-01-01T00:00:00+00:00",
            "ttl_hours": "invalid",
        }
        pin_path = agdt_dir / PIN_FILENAME
        pin_path.write_text(json.dumps(data), encoding="utf-8")

        with patch("agentic_devtools.state._get_git_repo_root", return_value=tmp_path):
            refresh_pin_file_ttl()

        result = json.loads(pin_path.read_text(encoding="utf-8"))
        assert result["created_utc"] == "2020-01-01T00:00:00+00:00"

    def test_noop_when_ttl_hours_zero(self, tmp_path):
        """No-op when ttl_hours is zero."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir(parents=True, exist_ok=True)
        state_dir = tmp_path / ".agdt" / "workflows" / "user" / "PROJ-1"
        state_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "state_dir": str(state_dir),
            "workflow": "pull-request-review",
            "created_utc": "2020-01-01T00:00:00+00:00",
            "ttl_hours": 0,
        }
        pin_path = agdt_dir / PIN_FILENAME
        pin_path.write_text(json.dumps(data), encoding="utf-8")

        with patch("agentic_devtools.state._get_git_repo_root", return_value=tmp_path):
            refresh_pin_file_ttl()

        result = json.loads(pin_path.read_text(encoding="utf-8"))
        assert result["created_utc"] == "2020-01-01T00:00:00+00:00"

    def test_noop_when_ttl_hours_negative(self, tmp_path):
        """No-op when ttl_hours is negative."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir(parents=True, exist_ok=True)
        state_dir = tmp_path / ".agdt" / "workflows" / "user" / "PROJ-1"
        state_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "state_dir": str(state_dir),
            "workflow": "pull-request-review",
            "created_utc": "2020-01-01T00:00:00+00:00",
            "ttl_hours": -5,
        }
        pin_path = agdt_dir / PIN_FILENAME
        pin_path.write_text(json.dumps(data), encoding="utf-8")

        with patch("agentic_devtools.state._get_git_repo_root", return_value=tmp_path):
            refresh_pin_file_ttl()

        result = json.loads(pin_path.read_text(encoding="utf-8"))
        assert result["created_utc"] == "2020-01-01T00:00:00+00:00"

    def test_noop_when_ttl_hours_boolean(self, tmp_path):
        """No-op when ttl_hours is a boolean (True is truthy but not valid)."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir(parents=True, exist_ok=True)
        state_dir = tmp_path / ".agdt" / "workflows" / "user" / "PROJ-1"
        state_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "state_dir": str(state_dir),
            "workflow": "pull-request-review",
            "created_utc": "2020-01-01T00:00:00+00:00",
            "ttl_hours": True,
        }
        pin_path = agdt_dir / PIN_FILENAME
        pin_path.write_text(json.dumps(data), encoding="utf-8")

        with patch("agentic_devtools.state._get_git_repo_root", return_value=tmp_path):
            refresh_pin_file_ttl()

        result = json.loads(pin_path.read_text(encoding="utf-8"))
        assert result["created_utc"] == "2020-01-01T00:00:00+00:00"

    def test_noop_when_state_dir_not_absolute(self, tmp_path):
        """No-op when state_dir is a relative path."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "state_dir": "relative/path",
            "workflow": "pull-request-review",
            "created_utc": "2020-01-01T00:00:00+00:00",
            "ttl_hours": 24,
        }
        pin_path = agdt_dir / PIN_FILENAME
        pin_path.write_text(json.dumps(data), encoding="utf-8")

        with patch("agentic_devtools.state._get_git_repo_root", return_value=tmp_path):
            refresh_pin_file_ttl()

        result = json.loads(pin_path.read_text(encoding="utf-8"))
        assert result["created_utc"] == "2020-01-01T00:00:00+00:00"

    def test_noop_when_state_dir_outside_repo(self, tmp_path):
        """No-op when state_dir is outside the repository root (traversal)."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir(parents=True, exist_ok=True)
        # state_dir points outside tmp_path (the simulated repo root)
        outside_dir = tmp_path.parent / "outside"
        outside_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "state_dir": str(outside_dir),
            "workflow": "pull-request-review",
            "created_utc": "2020-01-01T00:00:00+00:00",
            "ttl_hours": 24,
        }
        pin_path = agdt_dir / PIN_FILENAME
        pin_path.write_text(json.dumps(data), encoding="utf-8")

        with patch("agentic_devtools.state._get_git_repo_root", return_value=tmp_path):
            refresh_pin_file_ttl()

        result = json.loads(pin_path.read_text(encoding="utf-8"))
        assert result["created_utc"] == "2020-01-01T00:00:00+00:00"

    def test_noop_when_state_dir_inside_repo_but_outside_workflows(self, tmp_path):
        """No-op when state_dir is inside repo root but not under .agdt/workflows/."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir(parents=True, exist_ok=True)
        # state_dir is under repo root but not under .agdt/workflows/
        inside_repo_dir = tmp_path / "src"
        inside_repo_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "state_dir": str(inside_repo_dir),
            "workflow": "pull-request-review",
            "created_utc": "2020-01-01T00:00:00+00:00",
            "ttl_hours": 24,
        }
        pin_path = agdt_dir / PIN_FILENAME
        pin_path.write_text(json.dumps(data), encoding="utf-8")

        with patch("agentic_devtools.state._get_git_repo_root", return_value=tmp_path):
            refresh_pin_file_ttl()

        result = json.loads(pin_path.read_text(encoding="utf-8"))
        assert result["created_utc"] == "2020-01-01T00:00:00+00:00"
