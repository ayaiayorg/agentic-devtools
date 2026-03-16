"""Tests for agentic_devtools.state.set_bootstrap_state."""

import json
from unittest.mock import MagicMock, patch

from agentic_devtools import state


class TestSetBootstrapState:
    """Tests for writing the runtime bootstrap file."""

    def test_writes_bootstrap_file_with_identity_and_worktree_key(self, tmp_path):
        """Writes both identity and worktree_key to bootstrap file."""
        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.object(state, "_get_git_email", return_value="test@example.com"):
                state.set_bootstrap_state(identity="ama", worktree_key="DFLY-1234")

        bootstrap_path = tmp_path / ".agdt" / "runtime-bootstrap.json"
        assert bootstrap_path.exists()
        data = json.loads(bootstrap_path.read_text(encoding="utf-8"))
        assert data["identity"] == "ama"
        assert data["worktree_key"] == "DFLY-1234"

    def test_resolves_identity_automatically_when_not_provided(self, tmp_path):
        """Resolves identity via _resolve_identity when identity is None."""
        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.object(state, "_resolve_identity", return_value="xyz") as mock_resolve:
                mock_git = MagicMock()
                mock_git.returncode = 0
                mock_git.stdout = "user@example.com\n"
                with patch("agentic_devtools.state.subprocess.run", return_value=mock_git):
                    state.set_bootstrap_state(worktree_key="DFLY-99")

        mock_resolve.assert_called_once_with(tmp_path)
        bootstrap_path = tmp_path / ".agdt" / "runtime-bootstrap.json"
        data = json.loads(bootstrap_path.read_text(encoding="utf-8"))
        assert data["identity"] == "xyz"
        assert data["worktree_key"] == "DFLY-99"

    def test_creates_identity_owner_file(self, tmp_path):
        """Creates .identity-owner file under .agdt/workflows/{identity}/."""
        mock_git = MagicMock()
        mock_git.returncode = 0
        mock_git.stdout = "albert.marsnik@example.com\n"

        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch("agentic_devtools.state.subprocess.run", return_value=mock_git):
                state.set_bootstrap_state(identity="ama", worktree_key="DFLY-1")

        owner_file = tmp_path / ".agdt" / "workflows" / "ama" / ".identity-owner"
        assert owner_file.exists()
        assert owner_file.read_text(encoding="utf-8") == "albert.marsnik@example.com"

    def test_updates_worktree_key_preserving_identity(self, tmp_path):
        """Updating worktree_key preserves existing identity without re-resolving."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir(parents=True)
        (agdt_dir / "runtime-bootstrap.json").write_text(
            json.dumps({"identity": "ama", "worktree_key": "OLD-1"}), encoding="utf-8"
        )

        mock_git = MagicMock()
        mock_git.returncode = 0
        mock_git.stdout = "user@example.com\n"

        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch("agentic_devtools.state.subprocess.run", return_value=mock_git):
                with patch.object(state, "_resolve_identity") as mock_resolve:
                    state.set_bootstrap_state(worktree_key="NEW-2")

        # Identity was already in the file — _resolve_identity should NOT be called
        mock_resolve.assert_not_called()
        data = json.loads((agdt_dir / "runtime-bootstrap.json").read_text(encoding="utf-8"))
        assert data["identity"] == "ama"
        assert data["worktree_key"] == "NEW-2"

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
                state.set_bootstrap_state(identity="ama", worktree_key="DFLY-1")

        assert (tmp_path / ".agdt" / "runtime-bootstrap.json").exists()
        assert (tmp_path / ".agdt" / "workflows" / "ama").is_dir()


class TestSetBootstrapStateNormalization:
    """Tests for value normalization in set_bootstrap_state()."""

    def test_strips_whitespace_from_identity(self, tmp_path):
        """Leading/trailing whitespace on identity is stripped before writing."""
        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.object(state, "_get_git_email", return_value="u@e.com"):
                state.set_bootstrap_state(identity="  ama  ", worktree_key="K-1")

        data = json.loads((tmp_path / ".agdt" / "runtime-bootstrap.json").read_text(encoding="utf-8"))
        assert data["identity"] == "ama"
        # Identity dir should use the stripped name
        assert (tmp_path / ".agdt" / "workflows" / "ama").is_dir()

    def test_strips_whitespace_from_worktree_key(self, tmp_path):
        """Leading/trailing whitespace on worktree_key is stripped before writing."""
        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.object(state, "_get_git_email", return_value="u@e.com"):
                state.set_bootstrap_state(identity="ama", worktree_key="  DFLY-1  ")

        data = json.loads((tmp_path / ".agdt" / "runtime-bootstrap.json").read_text(encoding="utf-8"))
        assert data["worktree_key"] == "DFLY-1"

    def test_whitespace_only_identity_falls_back_to_resolve(self, tmp_path):
        """Whitespace-only identity is treated as None → falls back to auto-resolve."""
        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.object(state, "_resolve_identity", return_value="resolved") as mock_r:
                with patch.object(state, "_get_git_email", return_value="u@e.com"):
                    state.set_bootstrap_state(identity="   ", worktree_key="K-1")

        mock_r.assert_called_once()
        data = json.loads((tmp_path / ".agdt" / "runtime-bootstrap.json").read_text(encoding="utf-8"))
        assert data["identity"] == "resolved"

    def test_whitespace_only_worktree_key_clears_existing(self, tmp_path):
        """Whitespace-only worktree_key removes the key from bootstrap file."""
        agdt = tmp_path / ".agdt"
        agdt.mkdir(parents=True)
        (agdt / "runtime-bootstrap.json").write_text(
            json.dumps({"identity": "ama", "worktree_key": "OLD-1"}), encoding="utf-8"
        )
        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.object(state, "_get_git_email", return_value="u@e.com"):
                state.set_bootstrap_state(identity="ama", worktree_key="   ")

        data = json.loads((agdt / "runtime-bootstrap.json").read_text(encoding="utf-8"))
        assert "worktree_key" not in data
        assert data["identity"] == "ama"

    def test_empty_string_worktree_key_clears_existing(self, tmp_path):
        """Empty-string worktree_key removes the key from bootstrap file."""
        agdt = tmp_path / ".agdt"
        agdt.mkdir(parents=True)
        (agdt / "runtime-bootstrap.json").write_text(
            json.dumps({"identity": "ama", "worktree_key": "OLD-1"}), encoding="utf-8"
        )
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
        assert data["identity"] == "resolved"

    def test_handles_corrupted_existing_bootstrap(self, tmp_path):
        """Corrupted (non-UTF-8) existing bootstrap is treated as empty, not an error."""
        agdt = tmp_path / ".agdt"
        agdt.mkdir(parents=True)
        (agdt / "runtime-bootstrap.json").write_bytes(b"\x80\x81\x82\x83")
        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.object(state, "_get_git_email", return_value="u@e.com"):
                state.set_bootstrap_state(identity="ama", worktree_key="K-1")

        data = json.loads((agdt / "runtime-bootstrap.json").read_text(encoding="utf-8"))
        assert data["identity"] == "ama"
        assert data["worktree_key"] == "K-1"

    def test_identity_pops_when_resolve_fails(self, tmp_path):
        """When identity cannot be resolved at all, existing identity key is removed."""
        agdt = tmp_path / ".agdt"
        agdt.mkdir(parents=True)
        (agdt / "runtime-bootstrap.json").write_text(
            json.dumps({"identity": "", "worktree_key": "K-1"}), encoding="utf-8"
        )
        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.object(state, "_resolve_identity", return_value=""):
                with patch.object(state, "_get_git_email", return_value="u@e.com"):
                    state.set_bootstrap_state(worktree_key="K-2")

        data = json.loads((agdt / "runtime-bootstrap.json").read_text(encoding="utf-8"))
        assert "identity" not in data
        assert data["worktree_key"] == "K-2"


class TestSetBootstrapStateGitignore:
    """Tests for ensure_agdt_gitignore integration in set_bootstrap_state."""

    def test_calls_ensure_agdt_gitignore(self, tmp_path):
        """Verify ensure_agdt_gitignore is called with the resolved git_root."""
        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.object(state, "_get_git_email", return_value="u@e.com"):
                with patch("agentic_devtools.agdt_gitignore.ensure_agdt_gitignore") as mock_ensure:
                    state.set_bootstrap_state(identity="ama", worktree_key="K-1")

        mock_ensure.assert_called_once_with(tmp_path)

    def test_creates_gitignore_file(self, tmp_path):
        """Verify .agdt/.gitignore is actually created by set_bootstrap_state."""
        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.object(state, "_get_git_email", return_value="u@e.com"):
                state.set_bootstrap_state(identity="ama", worktree_key="K-1")

        gi_path = tmp_path / ".agdt" / ".gitignore"
        assert gi_path.exists()
        content = gi_path.read_text(encoding="utf-8")
        assert "runtime-bootstrap.json" in content
        assert "workflows/" in content
