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
