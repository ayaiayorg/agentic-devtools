"""Tests for get_commit_body_path function."""

from unittest.mock import patch

from agentic_devtools.cli.git.commit_body import get_commit_body_path


class TestGetCommitBodyPath:
    """Tests for get_commit_body_path."""

    def test_returns_path_under_files_subdir(self, tmp_path):
        """Test path is {state_dir}/files/commit-body.md."""
        with patch(
            "agentic_devtools.cli.git.commit_body.get_state_dir",
            return_value=tmp_path,
        ):
            result = get_commit_body_path()
            assert result == tmp_path / "files" / "commit-body.md"

    def test_returns_absolute_path(self, tmp_path):
        """Test the returned path is absolute."""
        with patch(
            "agentic_devtools.cli.git.commit_body.get_state_dir",
            return_value=tmp_path,
        ):
            result = get_commit_body_path()
            assert result.is_absolute()

    def test_different_state_dirs_produce_different_paths(self, tmp_path):
        """Test that different worktree state dirs produce different paths."""
        dir_a = tmp_path / "worktree_a"
        dir_b = tmp_path / "worktree_b"

        with patch(
            "agentic_devtools.cli.git.commit_body.get_state_dir",
            return_value=dir_a,
        ):
            path_a = get_commit_body_path()

        with patch(
            "agentic_devtools.cli.git.commit_body.get_state_dir",
            return_value=dir_b,
        ):
            path_b = get_commit_body_path()

        assert path_a != path_b
        assert "worktree_a" in str(path_a)
        assert "worktree_b" in str(path_b)
