"""Tests for _scan_activity_log_replies function."""

from agentic_devtools.cli.azure_devops.finalization.classification import _scan_activity_log_replies
from agentic_devtools.cli.azure_devops.finalization.models import EligibleComments


def _make_activity_log_thread(thread_id, comments):
    """Build an activity-log thread with given comments."""
    return {"id": thread_id, "comments": comments}


class TestScanActivityLogReplies:
    """Tests for _scan_activity_log_replies function."""

    def test_skips_comments_without_marker(self):
        """Should skip comments with no parseable marker (parsed is None)."""
        thread = _make_activity_log_thread(
            200,
            [
                {
                    "id": 2,
                    "content": "This is a plain text comment with no marker",
                    "author": {"id": "my-user"},
                },
            ],
        )
        result = EligibleComments()
        _scan_activity_log_replies(thread, "my-user", "sess-1", result)
        assert len(result.activity_log_entries) == 0
        assert len(result.skipped) == 0

    def test_skips_marker_with_non_activity_log_entry_type(self):
        """Should skip comments with valid marker but type != activity-log-entry."""
        thread = _make_activity_log_thread(
            200,
            [
                {
                    "id": 2,
                    "content": "<!-- agdt-review:v1 type:file-summary file:/src/a.py -->\nSome content",
                    "author": {"id": "my-user"},
                },
            ],
        )
        result = EligibleComments()
        _scan_activity_log_replies(thread, "my-user", "sess-1", result)
        assert len(result.activity_log_entries) == 0
        assert len(result.skipped) == 0

    def test_skips_activity_log_entry_by_different_author(self):
        """Should add to skipped list when activity-log-entry is authored by different user."""
        thread = _make_activity_log_thread(
            200,
            [
                {
                    "id": 2,
                    "content": "<!-- agdt-review:v1 type:activity-log-entry -->\nsess-1 content",
                    "author": {"id": "other-user"},
                },
            ],
        )
        result = EligibleComments()
        _scan_activity_log_replies(thread, "my-user", "sess-1", result)
        assert len(result.activity_log_entries) == 0
        assert len(result.skipped) == 1
        assert result.skipped[0]["thread_id"] == "200"
        assert result.skipped[0]["comment_id"] == "2"
        assert "not editable" in result.skipped[0]["reason"]

    def test_skips_entry_not_matching_session_id(self):
        """Should skip activity-log-entry when content does not contain latest session ID."""
        thread = _make_activity_log_thread(
            200,
            [
                {
                    "id": 2,
                    "content": "<!-- agdt-review:v1 type:activity-log-entry -->\nold-session content",
                    "author": {"id": "my-user"},
                },
            ],
        )
        result = EligibleComments()
        _scan_activity_log_replies(thread, "my-user", "sess-latest", result)
        assert len(result.activity_log_entries) == 0

    def test_includes_matching_entry(self):
        """Should include activity-log-entry matching author and session ID."""
        thread = _make_activity_log_thread(
            200,
            [
                {
                    "id": 2,
                    "content": "<!-- agdt-review:v1 type:activity-log-entry -->\nsess-1 session data",
                    "author": {"id": "my-user"},
                },
            ],
        )
        result = EligibleComments()
        _scan_activity_log_replies(thread, "my-user", "sess-1", result)
        assert len(result.activity_log_entries) == 1
        assert result.activity_log_entries[0].thread_id == 200
        assert result.activity_log_entries[0].comment_id == 2

    def test_handles_empty_comments(self):
        """Should handle thread with no comments."""
        thread = _make_activity_log_thread(200, [])
        result = EligibleComments()
        _scan_activity_log_replies(thread, "my-user", "sess-1", result)
        assert len(result.activity_log_entries) == 0

    def test_mixed_comments_filters_correctly(self):
        """Should process multiple comments with mixed types and authors."""
        thread = _make_activity_log_thread(
            200,
            [
                # Plain comment — no marker
                {"id": 1, "content": "Main thread comment", "author": {"id": "my-user"}},
                # Valid marker but wrong type
                {
                    "id": 2,
                    "content": "<!-- agdt-review:v1 type:overall-summary -->\nSummary",
                    "author": {"id": "my-user"},
                },
                # Valid activity-log-entry but wrong author
                {
                    "id": 3,
                    "content": "<!-- agdt-review:v1 type:activity-log-entry -->\nsess-1",
                    "author": {"id": "other"},
                },
                # Valid activity-log-entry, correct author, matching session
                {
                    "id": 4,
                    "content": "<!-- agdt-review:v1 type:activity-log-entry -->\nsess-1 data",
                    "author": {"id": "my-user"},
                },
            ],
        )
        result = EligibleComments()
        _scan_activity_log_replies(thread, "my-user", "sess-1", result)
        assert len(result.activity_log_entries) == 1
        assert result.activity_log_entries[0].comment_id == 4
        assert len(result.skipped) == 1  # the wrong-author entry
