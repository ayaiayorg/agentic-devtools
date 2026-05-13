"""Tests for trusted bot account filtering logic (T020).

Tests the filtering logic used by workflow-approval-monitor.yml to determine
whether a workflow run should be approved based on the PR author.
"""

import pytest


class TestTrustedBotFiltering:
    """Test trusted bot account filtering logic (FR-001, FR-002, FR-007)."""

    @pytest.fixture
    def trusted_accounts(self):
        """Standard trusted accounts list from config."""
        return ["copilot-swe-agent[bot]", "github-actions[bot]"]

    def _is_trusted(self, pr_author, trusted_accounts):
        """Replicate the case-insensitive matching logic from the workflow."""
        pr_author_lower = pr_author.lower()
        return any(account.lower() == pr_author_lower for account in trusted_accounts)

    def _is_same_repo(self, head_repo_full_name, base_repo_full_name):
        """Replicate the fork-check logic from the workflow."""
        return head_repo_full_name == base_repo_full_name

    def test_trusted_bot_is_approved(self, trusted_accounts):
        """Happy path: PR from trusted bot collaborator is eligible for approval."""
        assert self._is_trusted("copilot-swe-agent[bot]", trusted_accounts) is True

    def test_github_actions_bot_is_approved(self, trusted_accounts):
        """Happy path: github-actions[bot] is in the trusted list."""
        assert self._is_trusted("github-actions[bot]", trusted_accounts) is True

    def test_case_insensitive_matching(self, trusted_accounts):
        """Case-insensitive matching works for bot accounts."""
        assert self._is_trusted("Copilot-SWE-Agent[bot]", trusted_accounts) is True
        assert self._is_trusted("GITHUB-ACTIONS[BOT]", trusted_accounts) is True

    def test_non_listed_account_rejected(self, trusted_accounts):
        """PR from an account not in the trusted list is rejected."""
        assert self._is_trusted("random-user", trusted_accounts) is False
        assert self._is_trusted("malicious-bot[bot]", trusted_accounts) is False

    def test_fork_pr_rejected(self):
        """Fork PRs are always rejected regardless of author."""
        assert self._is_same_repo("attacker/repo", "owner/repo") is False

    def test_same_repo_pr_accepted(self):
        """Same-repo PRs pass the fork check."""
        assert self._is_same_repo("owner/repo", "owner/repo") is True

    def test_empty_author_rejected(self, trusted_accounts):
        """Empty author string is not in trusted list."""
        assert self._is_trusted("", trusted_accounts) is False

    def test_partial_match_rejected(self, trusted_accounts):
        """Partial matches (substrings) are not accepted — exact match only."""
        assert self._is_trusted("copilot-swe-agent", trusted_accounts) is False
        assert self._is_trusted("github-actions", trusted_accounts) is False
        assert self._is_trusted("[bot]", trusted_accounts) is False
