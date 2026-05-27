"""Tests for _collect_all_comments function in verification module."""

from agentic_devtools.cli.azure_devops.finalization.models import EligibleComment, EligibleComments
from agentic_devtools.cli.azure_devops.finalization.verification import _collect_all_comments


class TestCollectAllComments:
    """Tests for _collect_all_comments function."""

    def test_collects_file_summaries_only(self):
        """Should collect file summaries when no other types present."""
        fs = EligibleComment(
            thread_id=10,
            comment_id=1,
            marker_type="file-summary",
            marker_data={},
            current_content="content",
        )
        eligible = EligibleComments(file_summaries=[fs])
        result = _collect_all_comments(eligible)
        assert len(result) == 1
        assert result[0] is fs

    def test_collects_overall_summary(self):
        """Should include overall_summary when present."""
        os_ = EligibleComment(
            thread_id=100,
            comment_id=1,
            marker_type="overall-summary",
            marker_data={},
            current_content="overall",
        )
        eligible = EligibleComments(overall_summary=os_)
        result = _collect_all_comments(eligible)
        assert len(result) == 1
        assert result[0] is os_

    def test_collects_activity_log_entries(self):
        """Should include activity log entries."""
        al = EligibleComment(
            thread_id=200,
            comment_id=2,
            marker_type="activity-log-entry",
            marker_data={},
            current_content="log",
        )
        eligible = EligibleComments(activity_log_entries=[al])
        result = _collect_all_comments(eligible)
        assert len(result) == 1
        assert result[0] is al

    def test_collects_all_types(self):
        """Should collect all types in order: file_summaries, overall, activity_log."""
        fs = EligibleComment(
            thread_id=10,
            comment_id=1,
            marker_type="file-summary",
            marker_data={},
            current_content="fs",
        )
        os_ = EligibleComment(
            thread_id=100,
            comment_id=1,
            marker_type="overall-summary",
            marker_data={},
            current_content="os",
        )
        al = EligibleComment(
            thread_id=200,
            comment_id=2,
            marker_type="activity-log-entry",
            marker_data={},
            current_content="al",
        )
        eligible = EligibleComments(
            file_summaries=[fs],
            overall_summary=os_,
            activity_log_entries=[al],
        )
        result = _collect_all_comments(eligible)
        assert len(result) == 3
        assert result[0] is fs
        assert result[1] is os_
        assert result[2] is al

    def test_empty_eligible(self):
        """Should return empty list when no comments."""
        eligible = EligibleComments()
        result = _collect_all_comments(eligible)
        assert result == []

    def test_skips_overall_summary_when_none(self):
        """Should not include None overall_summary in result."""
        fs = EligibleComment(
            thread_id=10,
            comment_id=1,
            marker_type="file-summary",
            marker_data={},
            current_content="fs",
        )
        eligible = EligibleComments(file_summaries=[fs], overall_summary=None)
        result = _collect_all_comments(eligible)
        assert len(result) == 1
