"""Tests for resolve_repository_root function."""

from unittest.mock import Mock, patch


class TestResolveRepositoryRoot:
    """Tests for resolve_repository_root function."""

    def test_returns_explicit_repo_root(self, tmp_path):
        """Test explicit repo_root is returned without invoking git."""
        from agentic_devtools.cli.azure_devops.review_helpers import resolve_repository_root

        with patch("agentic_devtools.cli.azure_devops.review_helpers.subprocess.run") as mock_run:
            result = resolve_repository_root(tmp_path)

        assert result == tmp_path
        mock_run.assert_not_called()

    def test_returns_git_toplevel_when_available(self, tmp_path):
        """Test git toplevel discovery returns the reported repository root."""
        from agentic_devtools.cli.azure_devops.review_helpers import resolve_repository_root

        completed = Mock(returncode=0, stdout=f"{tmp_path}\n")

        with patch(
            "agentic_devtools.cli.azure_devops.review_helpers.subprocess.run",
            return_value=completed,
        ) as mock_run:
            result = resolve_repository_root()

        assert result == tmp_path
        mock_run.assert_called_once()

    def test_falls_back_to_cwd_when_git_returns_nonzero(self, tmp_path):
        """Test nonzero git exit falls back to the current working directory."""
        from agentic_devtools.cli.azure_devops.review_helpers import resolve_repository_root

        completed = Mock(returncode=1, stdout="")

        with patch(
            "agentic_devtools.cli.azure_devops.review_helpers.subprocess.run",
            return_value=completed,
        ):
            with patch(
                "agentic_devtools.cli.azure_devops.review_helpers.Path.cwd",
                return_value=tmp_path,
            ):
                result = resolve_repository_root()

        assert result == tmp_path

    def test_falls_back_to_cwd_when_git_raises_oserror(self, tmp_path):
        """Test git invocation errors fall back to the current working directory."""
        from agentic_devtools.cli.azure_devops.review_helpers import resolve_repository_root

        with patch(
            "agentic_devtools.cli.azure_devops.review_helpers.subprocess.run",
            side_effect=OSError("git unavailable"),
        ):
            with patch(
                "agentic_devtools.cli.azure_devops.review_helpers.Path.cwd",
                return_value=tmp_path,
            ):
                result = resolve_repository_root()

        assert result == tmp_path