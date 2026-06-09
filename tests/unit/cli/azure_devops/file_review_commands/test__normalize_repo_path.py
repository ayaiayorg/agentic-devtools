"""Tests for _normalize_repo_path."""

from agentic_devtools.cli.azure_devops.file_review_commands import _normalize_repo_path


class TestNormalizeRepoPath:
    """Tests for _normalize_repo_path."""

    def test_returns_none_for_blank_input(self):
        """Blank or whitespace-only paths should normalize to None."""
        assert _normalize_repo_path("") is None
        assert _normalize_repo_path("   ") is None
        assert _normalize_repo_path(None) is None

    def test_normalizes_slashes_and_leading_separator(self):
        """Paths should use forward slashes and a single leading slash."""
        assert _normalize_repo_path(r"src\app.py") == "/src/app.py"
        assert _normalize_repo_path("/src/app.py") == "/src/app.py"
