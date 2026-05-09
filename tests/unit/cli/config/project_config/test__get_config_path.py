"""Tests for _get_config_path."""

from unittest.mock import patch

from agentic_devtools.cli.config.project_config import _get_config_path


class TestGetConfigPath:
    """Tests for _get_config_path."""

    def test_returns_none_when_not_in_git_repo(self):
        """Returns None when _get_git_repo_root() returns None."""
        with patch("agentic_devtools.state._get_git_repo_root", return_value=None):
            assert _get_config_path() is None

    def test_returns_path_when_in_git_repo(self, tmp_path):
        """Returns the config path when _get_git_repo_root() returns a valid path."""
        with patch("agentic_devtools.state._get_git_repo_root", return_value=tmp_path):
            result = _get_config_path()

        assert result is not None
        assert result == tmp_path / ".agdt" / "config" / "project.json"

    def test_uses_explicit_git_root_without_cwd_detection(self, tmp_path):
        """When git_root is passed, uses it directly without calling _get_git_repo_root."""
        result = _get_config_path(git_root=tmp_path)

        assert result == tmp_path / ".agdt" / "config" / "project.json"

    def test_explicit_git_root_none_falls_back_to_detection(self):
        """When git_root is explicitly None, falls back to CWD-based detection."""
        with patch("agentic_devtools.state._get_git_repo_root", return_value=None):
            assert _get_config_path(git_root=None) is None
