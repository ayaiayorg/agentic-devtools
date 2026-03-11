"""Tests for agentic_devtools.state.set_bootstrap_state."""

import json
from unittest.mock import MagicMock, patch

from agentic_devtools import state


class TestSetBootstrapState:
    """Tests for writing the runtime bootstrap file."""

    def test_writes_bootstrap_file_with_identity_and_worktree_key(self, tmp_path):
        """Writes both identity and worktree_key to bootstrap file."""
        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.object(state, "_resolve_identity", return_value="ama"):
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
        """Updating worktree_key preserves existing identity."""
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
                state.set_bootstrap_state(worktree_key="NEW-2")

        data = json.loads(
            (agdt_dir / "runtime-bootstrap.json").read_text(encoding="utf-8")
        )
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
