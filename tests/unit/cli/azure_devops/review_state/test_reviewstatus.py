"""Tests for ReviewStatus enum."""

from agentic_devtools.cli.azure_devops.review_state import ReviewStatus


class TestReviewStatus:
    """Tests for ReviewStatus enum."""

    def test_unreviewed_value(self):
        """Test UNREVIEWED has correct string value."""
        assert ReviewStatus.UNREVIEWED == "unreviewed"
        assert ReviewStatus.UNREVIEWED.value == "unreviewed"

    def test_in_progress_value(self):
        """Test IN_PROGRESS has correct string value."""
        assert ReviewStatus.IN_PROGRESS == "in-progress"
        assert ReviewStatus.IN_PROGRESS.value == "in-progress"

    def test_approved_value(self):
        """Test APPROVED has correct string value."""
        assert ReviewStatus.APPROVED == "approved"
        assert ReviewStatus.APPROVED.value == "approved"

    def test_needs_work_value(self):
        """Test NEEDS_WORK has correct string value."""
        assert ReviewStatus.NEEDS_WORK == "needs-work"
        assert ReviewStatus.NEEDS_WORK.value == "needs-work"

    def test_is_string_enum(self):
        """Test that ReviewStatus is a str enum (comparable to strings)."""
        assert ReviewStatus.UNREVIEWED == "unreviewed"
        assert ReviewStatus.APPROVED != "unreviewed"

    def test_all_values(self):
        """Test all four status values are present."""
        values = {s.value for s in ReviewStatus}
        assert values == {"unreviewed", "in-progress", "approved", "needs-work"}
