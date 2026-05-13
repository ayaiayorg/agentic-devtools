"""Tests for check_fork_pr() guard."""

from agentic_devtools.cli.ci.guards import check_fork_pr


class TestCheckForkPR:
    """Tests for the fork PR guard."""

    def test_same_repo_not_fork(self) -> None:
        assert check_fork_pr("owner/repo", "owner/repo") is False

    def test_different_owner_is_fork(self) -> None:
        assert check_fork_pr("fork-user/repo", "owner/repo") is True

    def test_different_repo_name_is_fork(self) -> None:
        assert check_fork_pr("owner/repo-fork", "owner/repo") is True

    def test_empty_strings(self) -> None:
        assert check_fork_pr("", "") is False

    def test_cross_org_fork(self) -> None:
        assert check_fork_pr("org-b/project", "org-a/project") is True
