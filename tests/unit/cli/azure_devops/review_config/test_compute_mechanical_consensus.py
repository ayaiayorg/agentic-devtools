"""Tests for compute_mechanical_consensus function."""

from agentic_devtools.cli.azure_devops.review_config import (
    compute_mechanical_consensus,
)


class TestComputeMechanicalConsensus:
    """Tests for compute_mechanical_consensus."""

    def test_majority_all_approved(self):
        """Majority: all approved → approved."""
        assert compute_mechanical_consensus(["approved", "approved", "approved"], "majority") == "approved"

    def test_majority_two_of_three_approved(self):
        """Majority: 2/3 approved → approved."""
        assert compute_mechanical_consensus(["approved", "approved", "needs-work"], "majority") == "approved"

    def test_majority_one_of_three_approved(self):
        """Majority: 1/3 approved → needs-work."""
        assert compute_mechanical_consensus(["approved", "needs-work", "needs-work"], "majority") == "needs-work"

    def test_majority_tie_is_conservative(self):
        """Majority: tie → needs-work (conservative)."""
        assert compute_mechanical_consensus(["approved", "needs-work"], "majority") == "needs-work"

    def test_unanimous_all_agree(self):
        """Unanimous: all agree → that status."""
        assert compute_mechanical_consensus(["approved", "approved"], "unanimous") == "approved"

    def test_unanimous_disagreement(self):
        """Unanimous: any disagreement → needs-work."""
        assert compute_mechanical_consensus(["approved", "needs-work"], "unanimous") == "needs-work"

    def test_unanimous_all_needs_work(self):
        """Unanimous: all needs-work → needs-work."""
        assert compute_mechanical_consensus(["needs-work", "needs-work"], "unanimous") == "needs-work"

    def test_first_reviewer_wins_approved(self):
        """First-reviewer-wins: uses first verdict."""
        assert (
            compute_mechanical_consensus(["approved", "needs-work", "needs-work"], "first-reviewer-wins") == "approved"
        )

    def test_first_reviewer_wins_needs_work(self):
        """First-reviewer-wins: first says needs-work."""
        assert (
            compute_mechanical_consensus(["needs-work", "approved", "approved"], "first-reviewer-wins") == "needs-work"
        )

    def test_empty_verdicts(self):
        """Empty verdicts → needs-work."""
        assert compute_mechanical_consensus([], "majority") == "needs-work"

    def test_single_verdict_majority(self):
        """Single verdict with majority → that verdict."""
        assert compute_mechanical_consensus(["approved"], "majority") == "approved"

    def test_single_verdict_unanimous(self):
        """Single verdict with unanimous → that verdict."""
        assert compute_mechanical_consensus(["approved"], "unanimous") == "approved"

    def test_first_reviewer_wins_normalizes_unknown_verdict(self):
        """first-reviewer-wins normalizes non-'approved' to 'needs-work'."""
        assert compute_mechanical_consensus(["in-progress"], "first-reviewer-wins") == "needs-work"

    def test_unanimous_all_unknown_verdicts(self):
        """Unanimous with all-same unknown verdicts → needs-work (normalized)."""
        assert compute_mechanical_consensus(["in-progress", "in-progress"], "unanimous") == "needs-work"
