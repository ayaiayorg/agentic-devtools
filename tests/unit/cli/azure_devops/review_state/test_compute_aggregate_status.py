"""Tests for compute_aggregate_status function."""

from agentic_devtools.cli.azure_devops.review_state import compute_aggregate_status


class TestComputeAggregateStatus:
    """Tests for compute_aggregate_status."""

    def test_empty_list_returns_unreviewed(self):
        """Empty status list returns unreviewed."""
        assert compute_aggregate_status([]) == "unreviewed"

    def test_all_unreviewed_returns_unreviewed(self):
        """All unreviewed statuses return unreviewed."""
        assert compute_aggregate_status(["unreviewed", "unreviewed"]) == "unreviewed"

    def test_single_unreviewed_returns_unreviewed(self):
        """Single unreviewed status returns unreviewed."""
        assert compute_aggregate_status(["unreviewed"]) == "unreviewed"

    def test_some_approved_some_unreviewed_returns_in_progress(self):
        """Mix of approved and unreviewed returns in-progress."""
        assert compute_aggregate_status(["approved", "unreviewed"]) == "in-progress"

    def test_some_in_progress_some_unreviewed_returns_in_progress(self):
        """Mix of in-progress and unreviewed returns in-progress."""
        assert compute_aggregate_status(["in-progress", "unreviewed"]) == "in-progress"

    def test_all_in_progress_returns_in_progress(self):
        """All in-progress returns in-progress."""
        assert compute_aggregate_status(["in-progress", "in-progress"]) == "in-progress"

    def test_approved_and_in_progress_returns_in_progress(self):
        """Mix of approved and in-progress returns in-progress."""
        assert compute_aggregate_status(["approved", "in-progress"]) == "in-progress"

    def test_needs_work_and_unreviewed_returns_in_progress(self):
        """Mix of needs-work and unreviewed returns in-progress."""
        assert compute_aggregate_status(["needs-work", "unreviewed"]) == "in-progress"

    def test_needs_work_and_in_progress_returns_in_progress(self):
        """Mix of needs-work and in-progress returns in-progress."""
        assert compute_aggregate_status(["needs-work", "in-progress"]) == "in-progress"

    def test_all_approved_returns_approved(self):
        """All approved returns approved."""
        assert compute_aggregate_status(["approved", "approved"]) == "approved"

    def test_single_approved_returns_approved(self):
        """Single approved returns approved."""
        assert compute_aggregate_status(["approved"]) == "approved"

    def test_all_complete_any_needs_work_returns_needs_work(self):
        """All complete with any needs-work returns needs-work."""
        assert compute_aggregate_status(["approved", "needs-work"]) == "needs-work"

    def test_all_needs_work_returns_needs_work(self):
        """All needs-work returns needs-work."""
        assert compute_aggregate_status(["needs-work", "needs-work"]) == "needs-work"

    def test_single_needs_work_returns_needs_work(self):
        """Single needs-work returns needs-work."""
        assert compute_aggregate_status(["needs-work"]) == "needs-work"

    def test_all_four_statuses_returns_in_progress(self):
        """Mix of all four statuses returns in-progress (not all complete)."""
        statuses = ["approved", "needs-work", "in-progress", "unreviewed"]
        assert compute_aggregate_status(statuses) == "in-progress"
