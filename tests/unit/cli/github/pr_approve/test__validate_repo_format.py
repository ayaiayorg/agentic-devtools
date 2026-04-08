"""Tests for _validate_repo_format helper."""

import pytest

from agentic_devtools.cli.github.pr_approve import _validate_repo_format


class TestValidateRepoFormat:
    """Tests for _validate_repo_format."""

    def test_valid_owner_repo(self):
        """Returns (owner, repo) for valid input."""
        owner, repo = _validate_repo_format("owner/repo")
        assert owner == "owner"
        assert repo == "repo"

    def test_valid_with_dots_and_hyphens(self):
        """Handles owner/repo with dots and hyphens."""
        owner, repo = _validate_repo_format("my-org/my.repo-name")
        assert owner == "my-org"
        assert repo == "my.repo-name"

    def test_no_slash_exits(self):
        """sys.exit(1) when no slash present."""
        with pytest.raises(SystemExit) as exc_info:
            _validate_repo_format("noslash")
        assert exc_info.value.code == 1

    def test_empty_owner_exits(self):
        """sys.exit(1) when owner part is empty."""
        with pytest.raises(SystemExit) as exc_info:
            _validate_repo_format("/repo")
        assert exc_info.value.code == 1

    def test_empty_repo_exits(self):
        """sys.exit(1) when repo part is empty."""
        with pytest.raises(SystemExit) as exc_info:
            _validate_repo_format("owner/")
        assert exc_info.value.code == 1

    def test_whitespace_only_parts_exit(self):
        """sys.exit(1) when parts are whitespace-only."""
        with pytest.raises(SystemExit) as exc_info:
            _validate_repo_format("  /  ")
        assert exc_info.value.code == 1

    def test_extra_path_segments_exit(self):
        """sys.exit(1) when input has more than one slash (e.g. owner/repo/extra)."""
        with pytest.raises(SystemExit) as exc_info:
            _validate_repo_format("owner/repo/extra")
        assert exc_info.value.code == 1

    def test_strips_dot_git_suffix(self):
        """Strips trailing .git and returns valid (owner, repo)."""
        owner, repo = _validate_repo_format("owner/repo.git")
        assert owner == "owner"
        assert repo == "repo"

    def test_strips_whitespace_and_dot_git(self):
        """Handles leading/trailing whitespace combined with .git."""
        owner, repo = _validate_repo_format("  owner/repo.git  ")
        assert owner == "owner"
        assert repo == "repo"
