"""Tests for _collect_all_comments function."""

from agentic_devtools.cli.azure_devops.finalization.models import EligibleComment, EligibleComments
from agentic_devtools.cli.azure_devops.finalization.orchestrator import _collect_all_comments


class TestCollectAllComments:
    """Tests for _collect_all_comments function."""

    def test_empty_eligible(self):
        """Should return empty list for empty eligible comments."""
        assert _collect_all_comments(EligibleComments()) == []

    def test_collects_file_summaries(self):
        """Should include file summaries."""
        comment = EligibleComment(
            thread_id=1, comment_id=1, marker_type="file-summary",
            marker_data={}, current_content="a",
        )
        eligible = EligibleComments(file_summaries=[comment])
        result = _collect_all_comments(eligible)
        assert len(result) == 1
        assert result[0] is comment

    def test_collects_overall_summary(self):
        """Should include overall summary when present."""
        summary = EligibleComment(
            thread_id=100, comment_id=1, marker_type="overall-summary",
            marker_data={}, current_content="s",
        )
        eligible = EligibleComments(overall_summary=summary)
        result = _collect_all_comments(eligible)
        assert len(result) == 1
        assert result[0] is summary

    def test_collects_activity_log_entries(self):
        """Should include activity log entries."""
        entry = EligibleComment(
            thread_id=200, comment_id=2, marker_type="activity-log-entry",
            marker_data={}, current_content="l",
        )
        eligible = EligibleComments(activity_log_entries=[entry])
        result = _collect_all_comments(eligible)
        assert len(result) == 1
        assert result[0] is entry

    def test_collects_all_types(self):
        """Should collect all types in order: file_summaries, overall, activity_log."""
        fs = EligibleComment(thread_id=1, comment_id=1, marker_type="file-summary", marker_data={}, current_content="a")
        os_ = EligibleComment(thread_id=100, comment_id=1, marker_type="overall-summary", marker_data={}, current_content="s")
        al = EligibleComment(thread_id=200, comment_id=2, marker_type="activity-log-entry", marker_data={}, current_content="l")
        eligible = EligibleComments(file_summaries=[fs], overall_summary=os_, activity_log_entries=[al])
        result = _collect_all_comments(eligible)
        assert len(result) == 3
        assert result[0] is fs
        assert result[1] is os_
        assert result[2] is al
