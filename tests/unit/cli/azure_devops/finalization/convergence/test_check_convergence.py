"""Tests for check_convergence function."""

from agentic_devtools.cli.azure_devops.finalization.convergence import check_convergence
from agentic_devtools.cli.azure_devops.finalization.models import EligibleComment


class TestCheckConvergence:
    """Tests for check_convergence."""

    def test_exact_match_converged(self):
        """Should return True when observed matches expected."""
        comment = EligibleComment(
            thread_id=10,
            comment_id=1,
            marker_type="file-summary",
            marker_data={},
            current_content="<!-- agdt-review:v1 type:file-summary -->\n## Summary\nContent",
        )
        expected = "## Summary\nContent"
        assert check_convergence(comment, expected) is True

    def test_mismatch_not_converged(self):
        """Should return False when observed differs from expected."""
        comment = EligibleComment(
            thread_id=10,
            comment_id=1,
            marker_type="file-summary",
            marker_data={},
            current_content="<!-- agdt-review:v1 type:file-summary -->\n## Old Content",
        )
        expected = "## New Content"
        assert check_convergence(comment, expected) is False

    def test_whitespace_tolerance(self):
        """Should tolerate trailing whitespace differences."""
        comment = EligibleComment(
            thread_id=10,
            comment_id=1,
            marker_type="file-summary",
            marker_data={},
            current_content="<!-- agdt-review:v1 type:file-summary -->\n## Summary  \n",
        )
        expected = "## Summary"
        assert check_convergence(comment, expected) is True
