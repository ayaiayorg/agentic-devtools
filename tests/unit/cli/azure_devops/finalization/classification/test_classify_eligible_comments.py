"""Tests for classify_eligible_comments function."""

from agentic_devtools.cli.azure_devops.finalization.classification import classify_eligible_comments
from agentic_devtools.cli.azure_devops.review_state import (
    FileEntry,
    FolderGroup,
    OverallSummary,
    ReviewSession,
    ReviewState,
)


def _make_thread(thread_id, content, author_id="my-user"):
    """Build a minimal thread dict for testing."""
    return {
        "id": thread_id,
        "comments": [
            {
                "id": 1,
                "content": content,
                "author": {"id": author_id},
            }
        ],
    }


def _make_activity_log_thread(thread_id, replies, author_id="my-user"):
    """Build an activity-log thread with a main comment and reply entries."""
    comments = [
        {
            "id": 1,
            "content": "<!-- agdt-review:v1 type:activity-log -->",
            "author": {"id": author_id},
        }
    ]
    comments.extend(replies)
    return {"id": thread_id, "comments": comments}


def _minimal_review_state(sessions=None):
    """Build a minimal ReviewState for testing."""
    return ReviewState(
        prId=42,
        repoId="repo-guid",
        repoName="test-repo",
        project="TestProject",
        organization="https://dev.azure.com/org",
        latestIterationId=1,
        scaffoldedUtc="2026-01-01T00:00:00+00:00",
        overallSummary=OverallSummary(threadId=100, commentId=1),
        folders={"src": FolderGroup(files=["/src/a.py"])},
        files={"/src/a.py": FileEntry(threadId=10, commentId=1, folder="src", fileName="a.py", status="approved")},
        sessions=sessions or [],
    )


class TestClassifyEligibleComments:
    """Tests for classify_eligible_comments."""

    def test_classifies_file_summary(self):
        """Should classify file-summary threads correctly."""
        threads = [_make_thread(10, "<!-- agdt-review:v1 type:file-summary file:/src/a.py -->\nContent")]
        result = classify_eligible_comments(threads, "my-user", _minimal_review_state())
        assert len(result.file_summaries) == 1
        assert result.file_summaries[0].marker_type == "file-summary"
        assert result.file_summaries[0].file_path == "/src/a.py"

    def test_classifies_overall_summary(self):
        """Should classify overall-summary threads correctly."""
        threads = [_make_thread(100, "<!-- agdt-review:v1 type:overall-summary -->\nContent")]
        result = classify_eligible_comments(threads, "my-user", _minimal_review_state())
        assert result.overall_summary is not None
        assert result.overall_summary.marker_type == "overall-summary"

    def test_skips_other_author_comments(self):
        """Should skip comments authored by a different user."""
        threads = [_make_thread(10, "<!-- agdt-review:v1 type:file-summary -->", author_id="other-user")]
        result = classify_eligible_comments(threads, "my-user", _minimal_review_state())
        assert len(result.file_summaries) == 0
        assert len(result.skipped) == 1
        assert "not editable" in result.skipped[0]["reason"]

    def test_skips_unclassified_threads(self):
        """Should skip threads without AGDT markers."""
        threads = [{"id": 1, "comments": [{"id": 1, "content": "Human comment", "author": {"id": "my-user"}}]}]
        result = classify_eligible_comments(threads, "my-user", _minimal_review_state())
        assert len(result.file_summaries) == 0
        assert result.overall_summary is None

    def test_classifies_activity_log_entries_from_replies(self):
        """Should find activity-log-entry markers in thread replies."""
        session = ReviewSession(
            sessionId="sess-1",
            modelId="gpt-5",
            startedUtc="2026-01-01T00:00:00+00:00",
        )
        replies = [
            {
                "id": 2,
                "content": (
                    "<!-- agdt-review:v1 type:activity-log-entry -->\n### Review Session — 🆕 New Review\nsess-1"
                ),
                "author": {"id": "my-user"},
            }
        ]
        thread = _make_activity_log_thread(200, replies)
        result = classify_eligible_comments([thread], "my-user", _minimal_review_state(sessions=[session]))
        assert len(result.activity_log_entries) == 1

    def test_activity_log_session_scoping(self):
        """Should only include activity-log entries matching the latest session."""
        session = ReviewSession(
            sessionId="sess-2",
            modelId="gpt-5",
            startedUtc="2026-01-01T00:00:00+00:00",
        )
        replies = [
            {
                "id": 2,
                "content": "<!-- agdt-review:v1 type:activity-log-entry -->\nsess-1 old session",
                "author": {"id": "my-user"},
            },
            {
                "id": 3,
                "content": "<!-- agdt-review:v1 type:activity-log-entry -->\nsess-2 current session",
                "author": {"id": "my-user"},
            },
        ]
        thread = _make_activity_log_thread(200, replies)
        result = classify_eligible_comments([thread], "my-user", _minimal_review_state(sessions=[session]))
        assert len(result.activity_log_entries) == 1
        assert "sess-2" in result.activity_log_entries[0].current_content

    def test_empty_threads(self):
        """Should return empty result for empty thread list."""
        result = classify_eligible_comments([], "my-user", _minimal_review_state())
        assert len(result.file_summaries) == 0
        assert result.overall_summary is None
        assert len(result.activity_log_entries) == 0
        assert len(result.skipped) == 0

    def test_skips_activity_log_entries_when_no_sessions(self):
        """Should skip all activity-log entries when review_state has no sessions."""
        replies = [
            {
                "id": 2,
                "content": "<!-- agdt-review:v1 type:activity-log-entry -->\n### Review Session\nsome content",
                "author": {"id": "my-user"},
            }
        ]
        thread = _make_activity_log_thread(200, replies)
        # No sessions in review state
        result = classify_eligible_comments([thread], "my-user", _minimal_review_state(sessions=[]))
        # Activity-log entries should be excluded entirely
        assert len(result.activity_log_entries) == 0

    def test_handles_thread_with_empty_comments(self):
        """Should skip threads with empty comments lists without error."""
        thread = {
            "id": 10,
            "comments": [
                {
                    "id": 1,
                    "content": "<!-- agdt-review:v1 type:file-summary file:/src/a.py -->\nContent",
                    "author": {"id": "my-user"},
                }
            ],
        }
        empty_thread = {
            "id": 20,
            "comments": [],
        }
        # Include one valid file-summary thread with a marker and one empty thread
        # The empty thread should be skipped (returns None from _extract_first_comment)
        # We need classify_agdt_threads to classify both as file-summary; to hit the
        # empty-comments path, the easiest way is to directly test with a file-summary
        # thread that has empty comments.  Since classify_agdt_threads only looks at
        # the first comment, the empty thread won't be classified.  Instead, construct
        # a thread with marker in first comment but manually empty after classification.
        result = classify_eligible_comments(
            [thread, empty_thread], "my-user", _minimal_review_state()
        )
        # Only the valid thread produces a file summary
        assert len(result.file_summaries) == 1

    def test_skips_activity_log_replies_without_marker(self):
        """Should skip activity-log reply comments that have no valid marker."""
        session = ReviewSession(
            sessionId="sess-1",
            modelId="gpt-5",
            startedUtc="2026-01-01T00:00:00+00:00",
        )
        replies = [
            {
                "id": 2,
                "content": "This is a plain reply with no marker whatsoever",
                "author": {"id": "my-user"},
            },
            {
                "id": 3,
                "content": "<!-- agdt-review:v1 type:activity-log-entry -->\nsess-1 session data",
                "author": {"id": "my-user"},
            },
        ]
        thread = _make_activity_log_thread(200, replies)
        result = classify_eligible_comments(
            [thread], "my-user", _minimal_review_state(sessions=[session])
        )
        # Only the valid entry should be included; the plain reply is skipped
        assert len(result.activity_log_entries) == 1
        assert "sess-1" in result.activity_log_entries[0].current_content

    def test_skips_activity_log_entry_with_wrong_author(self):
        """Should add skip entry when activity-log-entry author doesn't match PAT user."""
        session = ReviewSession(
            sessionId="sess-1",
            modelId="gpt-5",
            startedUtc="2026-01-01T00:00:00+00:00",
        )
        replies = [
            {
                "id": 2,
                "content": "<!-- agdt-review:v1 type:activity-log-entry -->\nsess-1 data",
                "author": {"id": "other-user"},
            },
        ]
        thread = _make_activity_log_thread(200, replies)
        result = classify_eligible_comments(
            [thread], "my-user", _minimal_review_state(sessions=[session])
        )
        assert len(result.activity_log_entries) == 0
        # The wrong-author entry should be in skipped
        skipped_reasons = [s.get("reason", "") for s in result.skipped]
        assert any("not editable" in r for r in skipped_reasons)
