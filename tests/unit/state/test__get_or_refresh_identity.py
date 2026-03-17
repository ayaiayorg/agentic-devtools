"""Tests for agentic_devtools.state._get_or_refresh_identity."""

import json
from unittest.mock import patch

from agentic_devtools import state


class TestGetOrRefreshIdentity:
    """Tests for _get_or_refresh_identity function."""

    def test_returns_cached_identity_when_email_matches(self, tmp_path):
        """Returns cached identity without calling _resolve_identity when email matches."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        (agdt_dir / "identity.json").write_text(
            json.dumps({"identity": "ama", "email": "alice@example.com"}),
            encoding="utf-8",
        )

        with patch.object(state, "_get_git_email", return_value="alice@example.com"):
            with patch.object(state, "_resolve_identity") as mock_resolve:
                result = state._get_or_refresh_identity(tmp_path)

        assert result == "ama"
        mock_resolve.assert_not_called()

    def test_resolves_and_caches_when_no_cache_file(self, tmp_path):
        """Calls _resolve_identity and writes identity.json when cache is absent."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()

        with patch.object(state, "_get_git_email", return_value="bob@example.com"):
            with patch.object(state, "_resolve_identity", return_value="bob") as mock_resolve:
                result = state._get_or_refresh_identity(tmp_path)

        assert result == "bob"
        mock_resolve.assert_called_once_with(tmp_path, _email="bob@example.com")

        # identity.json was written
        cache = json.loads((agdt_dir / "identity.json").read_text(encoding="utf-8"))
        assert cache["identity"] == "bob"
        assert cache["email"] == "bob@example.com"

    def test_resolves_and_caches_when_email_changed(self, tmp_path):
        """Re-resolves identity when git email has changed since last cache write."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        # Cache was written for old email
        (agdt_dir / "identity.json").write_text(
            json.dumps({"identity": "old", "email": "old@example.com"}),
            encoding="utf-8",
        )

        with patch.object(state, "_get_git_email", return_value="new@example.com"):
            with patch.object(state, "_resolve_identity", return_value="new") as mock_resolve:
                result = state._get_or_refresh_identity(tmp_path)

        assert result == "new"
        mock_resolve.assert_called_once_with(tmp_path, _email="new@example.com")

        # Cache updated with new identity and email
        cache = json.loads((agdt_dir / "identity.json").read_text(encoding="utf-8"))
        assert cache["identity"] == "new"
        assert cache["email"] == "new@example.com"

    def test_resolves_when_email_empty_and_no_cache(self, tmp_path):
        """Calls _resolve_identity when git email is unavailable and no cache exists."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()

        with patch.object(state, "_get_git_email", return_value=""):
            with patch.object(state, "_resolve_identity", return_value="default") as mock_resolve:
                result = state._get_or_refresh_identity(tmp_path)

        assert result == "default"
        mock_resolve.assert_called_once_with(tmp_path, _email="")

    def test_does_not_use_stale_cache_when_email_empty_but_cache_has_email(self, tmp_path):
        """Does not use cache when current email is empty (can't confirm identity)."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        (agdt_dir / "identity.json").write_text(
            json.dumps({"identity": "ama", "email": "alice@example.com"}),
            encoding="utf-8",
        )

        with patch.object(state, "_get_git_email", return_value=""):
            with patch.object(state, "_resolve_identity", return_value="default") as mock_resolve:
                result = state._get_or_refresh_identity(tmp_path)

        # Empty current email means cache can't be validated → re-resolve
        assert result == "default"
        mock_resolve.assert_called_once_with(tmp_path, _email="")

    def test_creates_agdt_dir_if_missing(self, tmp_path):
        """Creates .agdt/ directory if it does not exist."""
        # tmp_path/.agdt does not exist
        with patch.object(state, "_get_git_email", return_value="a@b.com"):
            with patch.object(state, "_resolve_identity", return_value="xyz"):
                state._get_or_refresh_identity(tmp_path)

        agdt_dir = tmp_path / ".agdt"
        assert agdt_dir.is_dir()
        assert (agdt_dir / "identity.json").exists()

    def test_uses_supplied_email_without_calling_get_git_email(self, tmp_path):
        """When _email is supplied, _get_git_email() is not called."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()

        with patch.object(state, "_get_git_email") as mock_email:
            with patch.object(state, "_resolve_identity", return_value="xyz") as mock_resolve:
                result = state._get_or_refresh_identity(tmp_path, _email="supplied@example.com")

        assert result == "xyz"
        mock_email.assert_not_called()
        mock_resolve.assert_called_once_with(tmp_path, _email="supplied@example.com")

    def test_supplied_email_used_for_cache_hit(self, tmp_path):
        """Supplied _email is compared against cache without subprocess call."""
        import json as _json
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        (agdt_dir / "identity.json").write_text(
            _json.dumps({"identity": "ama", "email": "alice@example.com"}),
            encoding="utf-8",
        )

        with patch.object(state, "_get_git_email") as mock_email:
            result = state._get_or_refresh_identity(tmp_path, _email="alice@example.com")

        assert result == "ama"
        mock_email.assert_not_called()
