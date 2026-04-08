"""Tests for _validate_repo_format."""

from agentic_devtools.cli.github.repo_resolution import _validate_repo_format


class TestValidateRepoFormat:
    """Tests for _validate_repo_format."""

    def test_valid_owner_repo(self):
        """Returns stripped value for valid owner/repo."""
        assert _validate_repo_format("owner/repo") == "owner/repo"

    def test_strips_whitespace(self):
        """Strips leading/trailing whitespace."""
        assert _validate_repo_format("  owner/repo  ") == "owner/repo"

    def test_rejects_no_slash(self):
        """Returns None when no slash is present."""
        assert _validate_repo_format("justrepo") is None

    def test_rejects_multiple_slashes(self):
        """Returns None when more than one slash is present."""
        assert _validate_repo_format("a/b/c") is None

    def test_rejects_empty_owner(self):
        """Returns None when owner part is empty."""
        assert _validate_repo_format("/repo") is None

    def test_rejects_empty_repo_name(self):
        """Returns None when repo name part is empty."""
        assert _validate_repo_format("owner/") is None

    def test_rejects_empty_string(self):
        """Returns None for empty string."""
        assert _validate_repo_format("") is None

    def test_strips_trailing_dot_git(self):
        """Strips trailing .git suffix to normalize repo name."""
        assert _validate_repo_format("owner/repo.git") == "owner/repo"

    def test_strips_dot_git_with_whitespace(self):
        """Strips .git after whitespace stripping."""
        assert _validate_repo_format("  owner/repo.git  ") == "owner/repo"

    def test_rejects_dot_git_only_repo(self):
        """Returns None when repo name is just .git (becomes empty after strip)."""
        assert _validate_repo_format("owner/.git") is None
