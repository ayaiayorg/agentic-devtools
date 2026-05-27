"""Tests for _count_eligible function."""

from agentic_devtools.cli.azure_devops.finalization.models import EligibleComment, EligibleComments
from agentic_devtools.cli.azure_devops.finalization.orchestrator import _count_eligible


class TestCountEligible:
    """Tests for _count_eligible function."""

    def test_empty_eligible(self):
        """Should return 0 for empty eligible comments."""
        assert _count_eligible(EligibleComments()) == 0

    def test_file_summaries_only(self):
        """Should count file summaries."""
        eligible = EligibleComments(
            file_summaries=[
                EligibleComment(
                    thread_id=1, comment_id=1, marker_type="file-summary", marker_data={}, current_content="a"
                ),
                EligibleComment(
                    thread_id=2, comment_id=1, marker_type="file-summary", marker_data={}, current_content="b"
                ),
            ]
        )
        assert _count_eligible(eligible) == 2

    def test_with_overall_summary(self):
        """Should count overall summary as 1."""
        eligible = EligibleComments(
            overall_summary=EligibleComment(
                thread_id=100, comment_id=1, marker_type="overall-summary", marker_data={}, current_content="s"
            ),
        )
        assert _count_eligible(eligible) == 1

    def test_with_activity_log_entries(self):
        """Should count activity log entries."""
        eligible = EligibleComments(
            activity_log_entries=[
                EligibleComment(
                    thread_id=200, comment_id=2, marker_type="activity-log-entry", marker_data={}, current_content="l"
                ),
            ]
        )
        assert _count_eligible(eligible) == 1

    def test_combined(self):
        """Should count all types together."""
        eligible = EligibleComments(
            file_summaries=[
                EligibleComment(
                    thread_id=1, comment_id=1, marker_type="file-summary", marker_data={}, current_content="a"
                ),
            ],
            overall_summary=EligibleComment(
                thread_id=100, comment_id=1, marker_type="overall-summary", marker_data={}, current_content="s"
            ),
            activity_log_entries=[
                EligibleComment(
                    thread_id=200, comment_id=2, marker_type="activity-log-entry", marker_data={}, current_content="l"
                ),
            ],
        )
        assert _count_eligible(eligible) == 3
