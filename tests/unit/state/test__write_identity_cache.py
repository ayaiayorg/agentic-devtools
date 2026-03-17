"""Tests for agentic_devtools.state._write_identity_cache."""

import json

from agentic_devtools import state


class TestWriteIdentityCache:
    """Tests for _write_identity_cache function."""

    def test_writes_identity_json_file(self, tmp_path):
        """Writes identity.json with identity and email keys."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()

        state._write_identity_cache(agdt_dir, "ama", "alice@example.com")

        cache_path = agdt_dir / "identity.json"
        assert cache_path.exists()
        data = json.loads(cache_path.read_text(encoding="utf-8"))
        assert data["identity"] == "ama"
        assert data["email"] == "alice@example.com"

    def test_creates_agdt_dir_if_missing(self, tmp_path):
        """Creates .agdt/ directory if it does not already exist."""
        agdt_dir = tmp_path / ".agdt"
        assert not agdt_dir.exists()

        state._write_identity_cache(agdt_dir, "xyz", "x@y.com")

        assert agdt_dir.is_dir()
        assert (agdt_dir / "identity.json").exists()

    def test_overwrites_existing_cache(self, tmp_path):
        """Overwrites an existing identity.json with new values."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        (agdt_dir / "identity.json").write_text(
            json.dumps({"identity": "old", "email": "old@example.com"}),
            encoding="utf-8",
        )

        state._write_identity_cache(agdt_dir, "new", "new@example.com")

        data = json.loads((agdt_dir / "identity.json").read_text(encoding="utf-8"))
        assert data["identity"] == "new"
        assert data["email"] == "new@example.com"

    def test_silently_ignores_os_error(self, tmp_path, monkeypatch):
        """Does not raise when writing the file fails with OSError."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()

        def _raise(*args, **kwargs):
            raise OSError("permission denied")

        monkeypatch.setattr("pathlib.Path.write_text", _raise)

        # Should not raise
        state._write_identity_cache(agdt_dir, "ama", "a@b.com")

    def test_writes_empty_email(self, tmp_path):
        """Writes correctly when email is an empty string."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()

        state._write_identity_cache(agdt_dir, "def", "")

        data = json.loads((agdt_dir / "identity.json").read_text(encoding="utf-8"))
        assert data["identity"] == "def"
        assert data["email"] == ""
