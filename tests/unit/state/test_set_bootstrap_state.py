"""Tests for agentic_devtools.state.set_bootstrap_state."""

import json
from unittest.mock import MagicMock, patch

from agentic_devtools import state


class TestSetBootstrapState:
    """Tests for writing the runtime bootstrap file."""

    def test_writes_bootstrap_file_with_worktree_key_only(self, tmp_path):
        """Bootstrap file contains only worktree_key; identity goes to identity.json."""
        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.object(state, "_get_git_email", return_value="test@example.com"):
                state.set_bootstrap_state(identity="ama", worktree_key="PROJECT-1234")

        bootstrap_path = tmp_path / ".agdt" / "runtime-bootstrap.json"
        assert bootstrap_path.exists()
        data = json.loads(bootstrap_path.read_text(encoding="utf-8"))
        assert "identity" not in data  # Identity no longer stored in bootstrap
        assert data["worktree_key"] == "PROJECT-1234"

        # Identity is now in identity.json
        identity_path = tmp_path / ".agdt" / "identity.json"
        assert identity_path.exists()
        cache = json.loads(identity_path.read_text(encoding="utf-8"))
        assert cache["identity"] == "ama"
        assert cache["email"] == "test@example.com"

    def test_resolves_identity_automatically_when_not_provided(self, tmp_path):
        """Resolves identity via _resolve_identity when identity is None and cache is absent."""
        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.object(state, "_resolve_identity", return_value="xyz") as mock_resolve:
                mock_git = MagicMock()
                mock_git.returncode = 0
                mock_git.stdout = "user@example.com\n"
                with patch("agentic_devtools.state.subprocess.run", return_value=mock_git):
                    state.set_bootstrap_state(worktree_key="PROJECT-99")

        mock_resolve.assert_called_once_with(tmp_path, _email="user@example.com")
        bootstrap_path = tmp_path / ".agdt" / "runtime-bootstrap.json"
        data = json.loads(bootstrap_path.read_text(encoding="utf-8"))
        assert "identity" not in data  # Identity no longer in bootstrap
        assert data["worktree_key"] == "PROJECT-99"

        # Identity is in identity.json
        cache = json.loads((tmp_path / ".agdt" / "identity.json").read_text(encoding="utf-8"))
        assert cache["identity"] == "xyz"

    def test_creates_identity_owner_file(self, tmp_path):
        """Creates .identity-owner file under .agdt/workflows/{identity}/."""
        mock_git = MagicMock()
        mock_git.returncode = 0
        mock_git.stdout = "albert.marsnik@example.com\n"

        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch("agentic_devtools.state.subprocess.run", return_value=mock_git):
                state.set_bootstrap_state(identity="ama", worktree_key="PROJECT-1")

        owner_file = tmp_path / ".agdt" / "workflows" / "ama" / ".identity-owner"
        assert owner_file.exists()
        assert owner_file.read_text(encoding="utf-8") == "albert.marsnik@example.com"

    def test_updates_worktree_key_using_cached_identity(self, tmp_path):
        """Updating worktree_key uses cached identity.json without re-resolving."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir(parents=True)
        # Identity now lives in identity.json, not bootstrap
        (agdt_dir / "identity.json").write_text(
            json.dumps({"identity": "ama", "email": "user@example.com"}), encoding="utf-8"
        )
        (agdt_dir / "runtime-bootstrap.json").write_text(json.dumps({"worktree_key": "OLD-1"}), encoding="utf-8")

        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.object(state, "_get_git_email", return_value="user@example.com"):
                with patch.object(state, "_resolve_identity") as mock_resolve:
                    state.set_bootstrap_state(worktree_key="NEW-2")

        # Cache is fresh (email matches) → _resolve_identity should NOT be called
        mock_resolve.assert_not_called()
        data = json.loads((agdt_dir / "runtime-bootstrap.json").read_text(encoding="utf-8"))
        assert "identity" not in data
        assert data["worktree_key"] == "NEW-2"

        # identity.json still has the original identity
        cache = json.loads((agdt_dir / "identity.json").read_text(encoding="utf-8"))
        assert cache["identity"] == "ama"

    def test_noop_when_not_in_git_repo(self, tmp_path):
        """set_bootstrap_state is a silent no-op when not in a git repo."""
        with patch.object(state, "_get_git_repo_root", return_value=None):
            state.set_bootstrap_state(identity="abc", worktree_key="XYZ-1")

        # No files should be created
        assert not (tmp_path / ".agdt").exists()

    def test_creates_directories(self, tmp_path):
        """Directories are created automatically."""
        mock_git = MagicMock()
        mock_git.returncode = 0
        mock_git.stdout = "user@example.com\n"

        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch("agentic_devtools.state.subprocess.run", return_value=mock_git):
                state.set_bootstrap_state(identity="ama", worktree_key="PROJECT-1")

        assert (tmp_path / ".agdt" / "runtime-bootstrap.json").exists()
        assert (tmp_path / ".agdt" / "identity.json").exists()
        assert (tmp_path / ".agdt" / "workflows" / "ama").is_dir()

    def test_calls_ensure_agdt_gitignore(self, tmp_path):
        """set_bootstrap_state calls ensure_agdt_gitignore with the resolved git_root."""
        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.object(state, "_get_git_email", return_value="test@example.com"):
                with patch("agentic_devtools.agdt_gitignore.ensure_agdt_gitignore") as mock_gitignore:
                    state.set_bootstrap_state(identity="ama", worktree_key="PROJECT-1")

        mock_gitignore.assert_called_once_with(tmp_path)


class TestSetBootstrapStateNormalization:
    """Tests for value normalization in set_bootstrap_state()."""

    def test_strips_whitespace_from_identity(self, tmp_path):
        """Leading/trailing whitespace on identity is stripped before writing to identity.json."""
        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.object(state, "_get_git_email", return_value="u@e.com"):
                state.set_bootstrap_state(identity="  ama  ", worktree_key="K-1")

        # identity.json should have stripped identity
        cache = json.loads((tmp_path / ".agdt" / "identity.json").read_text(encoding="utf-8"))
        assert cache["identity"] == "ama"
        # Bootstrap should have no identity key
        data = json.loads((tmp_path / ".agdt" / "runtime-bootstrap.json").read_text(encoding="utf-8"))
        assert "identity" not in data
        # Identity dir should use the stripped name
        assert (tmp_path / ".agdt" / "workflows" / "ama").is_dir()

    def test_strips_whitespace_from_worktree_key(self, tmp_path):
        """Leading/trailing whitespace on worktree_key is stripped before writing."""
        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.object(state, "_get_git_email", return_value="u@e.com"):
                state.set_bootstrap_state(identity="ama", worktree_key="  PROJECT-1  ")

        data = json.loads((tmp_path / ".agdt" / "runtime-bootstrap.json").read_text(encoding="utf-8"))
        assert data["worktree_key"] == "PROJECT-1"

    def test_whitespace_only_identity_falls_back_to_resolve(self, tmp_path):
        """Whitespace-only identity is treated as None → falls back to _get_or_refresh_identity."""
        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.object(state, "_resolve_identity", return_value="resolved") as mock_r:
                with patch.object(state, "_get_git_email", return_value="u@e.com"):
                    state.set_bootstrap_state(identity="   ", worktree_key="K-1")

        mock_r.assert_called_once()
        # Bootstrap has no identity; identity is in identity.json
        data = json.loads((tmp_path / ".agdt" / "runtime-bootstrap.json").read_text(encoding="utf-8"))
        assert "identity" not in data
        cache = json.loads((tmp_path / ".agdt" / "identity.json").read_text(encoding="utf-8"))
        assert cache["identity"] == "resolved"

    def test_unsafe_identity_falls_back_to_resolve(self, tmp_path):
        """Identity with unsafe path characters falls back to _get_or_refresh_identity.

        Identities like '../escape' would escape .agdt/workflows/ if used directly as path
        segments.  is_safe_dir_segment() rejects them, causing set_bootstrap_state() to
        resolve a safe identity instead.
        """
        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.object(state, "_resolve_identity", return_value="safe") as mock_r:
                with patch.object(state, "_get_git_email", return_value="u@e.com"):
                    state.set_bootstrap_state(identity="../escape", worktree_key="K-1")

        mock_r.assert_called_once()
        # The unsafe value must never appear in identity.json
        cache = json.loads((tmp_path / ".agdt" / "identity.json").read_text(encoding="utf-8"))
        assert cache["identity"] == "safe"
        assert cache["identity"] != "../escape"

    def test_whitespace_only_worktree_key_clears_existing(self, tmp_path):
        """Whitespace-only worktree_key removes the key from bootstrap file."""
        agdt = tmp_path / ".agdt"
        agdt.mkdir(parents=True)
        (agdt / "runtime-bootstrap.json").write_text(json.dumps({"worktree_key": "OLD-1"}), encoding="utf-8")
        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.object(state, "_get_git_email", return_value="u@e.com"):
                state.set_bootstrap_state(identity="ama", worktree_key="   ")

        data = json.loads((agdt / "runtime-bootstrap.json").read_text(encoding="utf-8"))
        assert "worktree_key" not in data
        assert "identity" not in data

    def test_empty_string_worktree_key_clears_existing(self, tmp_path):
        """Empty-string worktree_key removes the key from bootstrap file."""
        agdt = tmp_path / ".agdt"
        agdt.mkdir(parents=True)
        (agdt / "runtime-bootstrap.json").write_text(json.dumps({"worktree_key": "OLD-1"}), encoding="utf-8")
        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.object(state, "_get_git_email", return_value="u@e.com"):
                state.set_bootstrap_state(identity="ama", worktree_key="")

        data = json.loads((agdt / "runtime-bootstrap.json").read_text(encoding="utf-8"))
        assert "worktree_key" not in data

    def test_non_str_identity_falls_back_to_resolve(self, tmp_path):
        """Non-string identity (e.g., int) is treated as None → auto-resolve."""
        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.object(state, "_resolve_identity", return_value="resolved") as mock_r:
                with patch.object(state, "_get_git_email", return_value="u@e.com"):
                    state.set_bootstrap_state(identity=42, worktree_key="K-1")  # type: ignore[arg-type]

        mock_r.assert_called_once()
        data = json.loads((tmp_path / ".agdt" / "runtime-bootstrap.json").read_text(encoding="utf-8"))
        assert "identity" not in data
        cache = json.loads((tmp_path / ".agdt" / "identity.json").read_text(encoding="utf-8"))
        assert cache["identity"] == "resolved"

    def test_handles_corrupted_existing_bootstrap(self, tmp_path):
        """Corrupted (non-UTF-8) existing bootstrap is treated as empty, not an error."""
        agdt = tmp_path / ".agdt"
        agdt.mkdir(parents=True)
        (agdt / "runtime-bootstrap.json").write_bytes(b"\x80\x81\x82\x83")
        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.object(state, "_get_git_email", return_value="u@e.com"):
                state.set_bootstrap_state(identity="ama", worktree_key="K-1")

        data = json.loads((agdt / "runtime-bootstrap.json").read_text(encoding="utf-8"))
        assert "identity" not in data
        assert data["worktree_key"] == "K-1"
        cache = json.loads((agdt / "identity.json").read_text(encoding="utf-8"))
        assert cache["identity"] == "ama"

    def test_identity_written_to_cache_even_on_empty_resolution(self, tmp_path):
        """When _resolve_identity returns empty, identity.json is still written (with empty)."""
        agdt = tmp_path / ".agdt"
        agdt.mkdir(parents=True)
        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.object(state, "_resolve_identity", return_value=""):
                with patch.object(state, "_get_git_email", return_value="u@e.com"):
                    state.set_bootstrap_state(worktree_key="K-2")

        # Bootstrap has no identity
        data = json.loads((agdt / "runtime-bootstrap.json").read_text(encoding="utf-8"))
        assert "identity" not in data
        assert data["worktree_key"] == "K-2"
        # identity.json was written (empty identity)
        cache = json.loads((agdt / "identity.json").read_text(encoding="utf-8"))
        assert cache["identity"] == ""
        assert cache["email"] == "u@e.com"

    def test_unsafe_resolved_identity_treated_as_absent(self, tmp_path):
        """Unsafe identity from _get_or_refresh_identity() is treated as '' (no owner dir)."""
        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.object(state, "_get_or_refresh_identity", return_value="../../escape"):
                with patch.object(state, "_get_git_email", return_value="u@e.com"):
                    state.set_bootstrap_state(worktree_key="K-unsafe")

        # No identity directory should be created for the unsafe value
        assert not (tmp_path / ".agdt" / "workflows" / "../../escape").exists()
        assert not (tmp_path / ".agdt" / "workflows" / "_unscoped").exists()
        # Bootstrap still has the worktree_key, no identity key
        data = json.loads((tmp_path / ".agdt" / "runtime-bootstrap.json").read_text(encoding="utf-8"))
        assert data["worktree_key"] == "K-unsafe"
        assert "identity" not in data

    def test_get_git_email_called_only_once(self, tmp_path):
        """_get_git_email() is called exactly once per set_bootstrap_state() call."""
        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.object(state, "_get_git_email", return_value="u@e.com") as mock_email:
                with patch.object(state, "_resolve_identity", return_value="xyz"):
                    state.set_bootstrap_state(worktree_key="K-1")

        mock_email.assert_called_once()

    def test_get_git_email_called_only_once_with_explicit_identity(self, tmp_path):
        """_get_git_email() is called exactly once even when identity is provided explicitly."""
        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.object(state, "_get_git_email", return_value="u@e.com") as mock_email:
                state.set_bootstrap_state(identity="ama", worktree_key="K-1")

        mock_email.assert_called_once()
