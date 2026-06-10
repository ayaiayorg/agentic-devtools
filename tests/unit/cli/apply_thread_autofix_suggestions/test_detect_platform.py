"""Tests for _detect_platform."""

from unittest.mock import patch

from agentic_devtools.cli.apply_thread_autofix_suggestions import _detect_platform


class TestDetectPlatform:
    """Tests for platform detection."""

    def test_returns_github_from_config(self) -> None:
        with (
            patch("agentic_devtools.state._get_git_repo_root") as mock_root,
            patch("agentic_devtools.cli.apply_thread_autofix_suggestions.load_platform_config") as mock_load,
        ):
            mock_root.return_value = "/fake/repo"
            mock_load.return_value = {"code_hosting": "github"}
            result = _detect_platform()
        assert result == "github"

    def test_returns_azure_devops_from_config(self) -> None:
        with (
            patch("agentic_devtools.state._get_git_repo_root") as mock_root,
            patch("agentic_devtools.cli.apply_thread_autofix_suggestions.load_platform_config") as mock_load,
        ):
            mock_root.return_value = "/fake/repo"
            mock_load.return_value = {"code_hosting": "azure_devops"}
            result = _detect_platform()
        assert result == "azure_devops"

    def test_defaults_to_github_on_exception(self) -> None:
        with patch("agentic_devtools.state._get_git_repo_root") as mock_root:
            mock_root.side_effect = RuntimeError("oops")
            result = _detect_platform()
        assert result == "github"

    def test_defaults_to_github_when_no_git_root(self) -> None:
        with patch("agentic_devtools.state._get_git_repo_root") as mock_root:
            mock_root.return_value = None
            result = _detect_platform()
        assert result == "github"

    def test_defaults_to_github_on_unknown_platform_value(self) -> None:
        with (
            patch("agentic_devtools.state._get_git_repo_root") as mock_root,
            patch("agentic_devtools.cli.apply_thread_autofix_suggestions.load_platform_config") as mock_load,
        ):
            mock_root.return_value = "/fake/repo"
            mock_load.return_value = {"code_hosting": "gitlab"}
            result = _detect_platform()
        assert result == "github"
