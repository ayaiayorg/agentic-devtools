"""Tests for _normalize_repo function."""

import pytest

from agentic_devtools.cli.github.pr_checks_status import _normalize_repo


class TestNormalizeRepo:
    """Tests for repo string validation and normalization."""

    def test_valid_owner_repo(self):
        """Returns valid owner/repo unchanged."""
        assert _normalize_repo("owner/repo") == "owner/repo"

    def test_strips_whitespace(self):
        """Strips leading and trailing whitespace."""
        assert _normalize_repo("  owner/repo  ") == "owner/repo"

    def test_strips_trailing_git(self):
        """Strips trailing .git suffix."""
        assert _normalize_repo("owner/repo.git") == "owner/repo"

    def test_strips_whitespace_and_git(self):
        """Strips both whitespace and .git suffix."""
        assert _normalize_repo("  owner/repo.git  ") == "owner/repo"

    def test_no_slash_exits(self):
        """sys.exit(1) when repo has no slash."""
        with pytest.raises(SystemExit) as exc_info:
            _normalize_repo("noslash")
        assert exc_info.value.code == 1

    def test_multiple_slashes_exits(self):
        """sys.exit(1) when repo has more than one slash."""
        with pytest.raises(SystemExit) as exc_info:
            _normalize_repo("a/b/c")
        assert exc_info.value.code == 1

    def test_empty_string_exits(self):
        """sys.exit(1) on empty string."""
        with pytest.raises(SystemExit) as exc_info:
            _normalize_repo("")
        assert exc_info.value.code == 1

    def test_only_git_suffix_exits(self):
        """sys.exit(1) when string is just '.git'."""
        with pytest.raises(SystemExit) as exc_info:
            _normalize_repo(".git")
        assert exc_info.value.code == 1

    def test_empty_owner_exits(self):
        """sys.exit(1) when owner is empty (e.g. '/repo')."""
        with pytest.raises(SystemExit) as exc_info:
            _normalize_repo("/repo")
        assert exc_info.value.code == 1

    def test_empty_repo_name_exits(self):
        """sys.exit(1) when repo name is empty (e.g. 'owner/')."""
        with pytest.raises(SystemExit) as exc_info:
            _normalize_repo("owner/")
        assert exc_info.value.code == 1
