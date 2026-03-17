"""Tests for agentic_devtools.state._read_identity_cache."""

import json

from agentic_devtools import state


class TestReadIdentityCache:
    """Tests for _read_identity_cache function."""

    def test_returns_identity_and_email_when_file_valid(self, tmp_path):
        """Returns dict with identity and email when identity.json is valid."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        (agdt_dir / "identity.json").write_text(
            json.dumps({"identity": "ama", "email": "alice@example.com"}),
            encoding="utf-8",
        )

        result = state._read_identity_cache(agdt_dir)

        assert result is not None
        assert result["identity"] == "ama"
        assert result["email"] == "alice@example.com"

    def test_returns_none_when_file_missing(self, tmp_path):
        """Returns None when identity.json does not exist."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()

        result = state._read_identity_cache(agdt_dir)

        assert result is None

    def test_returns_none_when_identity_empty_string(self, tmp_path):
        """Returns None when identity is an empty string (stripped)."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        (agdt_dir / "identity.json").write_text(
            json.dumps({"identity": "   ", "email": "a@b.com"}),
            encoding="utf-8",
        )

        result = state._read_identity_cache(agdt_dir)

        assert result is None

    def test_returns_none_when_identity_missing(self, tmp_path):
        """Returns None when identity key is absent from the file."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        (agdt_dir / "identity.json").write_text(
            json.dumps({"email": "a@b.com"}),
            encoding="utf-8",
        )

        result = state._read_identity_cache(agdt_dir)

        assert result is None

    def test_returns_none_when_email_missing(self, tmp_path):
        """Returns None when email key is absent (identity requires both keys)."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        (agdt_dir / "identity.json").write_text(
            json.dumps({"identity": "ama"}),
            encoding="utf-8",
        )

        result = state._read_identity_cache(agdt_dir)

        assert result is None

    def test_returns_none_on_malformed_json(self, tmp_path):
        """Returns None when the file contains invalid JSON."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        (agdt_dir / "identity.json").write_text("not json!", encoding="utf-8")

        result = state._read_identity_cache(agdt_dir)

        assert result is None

    def test_returns_none_on_non_dict_json(self, tmp_path):
        """Returns None when file contains valid JSON but not a dict."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        (agdt_dir / "identity.json").write_text(json.dumps(["a", "b"]), encoding="utf-8")

        result = state._read_identity_cache(agdt_dir)

        assert result is None

    def test_returns_none_on_invalid_encoding(self, tmp_path):
        """Returns None when file has invalid UTF-8 bytes."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        (agdt_dir / "identity.json").write_bytes(b"\x80\x81\x82")

        result = state._read_identity_cache(agdt_dir)

        assert result is None

    def test_strips_whitespace_from_identity(self, tmp_path):
        """Identity value is stripped of leading/trailing whitespace."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        (agdt_dir / "identity.json").write_text(
            json.dumps({"identity": "  ama  ", "email": "a@b.com"}),
            encoding="utf-8",
        )

        result = state._read_identity_cache(agdt_dir)

        assert result is not None
        assert result["identity"] == "ama"

    def test_email_can_be_empty_string(self, tmp_path):
        """Email can be an empty string (e.g., when git config user.email is unset)."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        (agdt_dir / "identity.json").write_text(
            json.dumps({"identity": "def", "email": ""}),
            encoding="utf-8",
        )

        result = state._read_identity_cache(agdt_dir)

        assert result is not None
        assert result["identity"] == "def"
        assert result["email"] == ""

    def test_returns_none_when_cached_identity_is_unsafe(self, tmp_path):
        """Unsafe cached identity is rejected without self-healing; caller re-resolves."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        cache_path = agdt_dir / "identity.json"
        cache_path.write_text(
            json.dumps({"identity": "../bad", "email": "alice@example.com"}),
            encoding="utf-8",
        )

        result = state._read_identity_cache(agdt_dir)

        # Unsafe identity → None; the cache file must NOT be rewritten
        assert result is None
        unchanged = json.loads(cache_path.read_text(encoding="utf-8"))
        assert unchanged["identity"] == "../bad"
