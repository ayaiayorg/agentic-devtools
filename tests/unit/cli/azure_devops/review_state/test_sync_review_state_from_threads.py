"""Tests for sync_review_state_from_threads function."""

from typing import Any

from agentic_devtools.cli.azure_devops.review_state import (
    FileEntry,
    OverallSummary,
    ReviewState,
    ReviewStatus,
    sync_review_state_from_threads,
)


def _make_thread(thread_id: int, comment_id: int, content: str) -> dict:
    """Build a minimal thread dict."""
    return {"id": thread_id, "comments": [{"id": comment_id, "content": content}]}


def _make_review_state(**kwargs: Any) -> ReviewState:
    """Build a minimal ReviewState for testing."""
    defaults: dict[str, Any] = {
        "prId": 100,
        "repoId": "repo-id",
        "repoName": "test-repo",
        "project": "TestProject",
        "organization": "TestOrg",
        "latestIterationId": 1,
        "scaffoldedUtc": "2026-01-01T00:00:00Z",
        "overallSummary": OverallSummary(threadId=0, commentId=0),
        "folders": {},
        "files": {},
    }
    defaults.update(kwargs)
    return ReviewState(**defaults)


class TestSyncReviewStateFromThreads:
    """Tests for sync_review_state_from_threads."""

    def test_adds_missing_file_entry(self):
        """Adds a FileEntry for a marker-identified file-summary thread."""
        threads = [
            _make_thread(
                10,
                20,
                "<!-- agdt-review:v1 type:file-summary file:/src/app.ts pr:100 -->\nSummary",
            ),
        ]
        state = _make_review_state()
        result = sync_review_state_from_threads(100, threads, state)
        assert "/src/app.ts" in result.files
        entry = result.files["/src/app.ts"]
        assert entry.threadId == 10
        assert entry.commentId == 20
        assert entry.status == ReviewStatus.UNREVIEWED.value
        assert entry.folder == "src"
        assert entry.fileName == "app.ts"

    def test_skips_existing_file_entry(self):
        """Does not overwrite an existing FileEntry."""
        existing_entry = FileEntry(
            threadId=99,
            commentId=88,
            folder="src",
            fileName="app.ts",
            status=ReviewStatus.APPROVED.value,
        )
        state = _make_review_state(files={"/src/app.ts": existing_entry})
        threads = [
            _make_thread(
                10,
                20,
                "<!-- agdt-review:v1 type:file-summary file:/src/app.ts pr:100 -->\nNew",
            ),
        ]
        result = sync_review_state_from_threads(100, threads, state)
        assert result.files["/src/app.ts"].threadId == 99  # Not overwritten

    def test_updates_overall_summary_when_zero(self):
        """Updates overallSummary if threadId is 0."""
        threads = [
            _make_thread(
                50,
                60,
                "<!-- agdt-review:v1 type:overall-summary pr:100 -->\nOverall",
            ),
        ]
        state = _make_review_state()
        result = sync_review_state_from_threads(100, threads, state)
        assert result.overallSummary.threadId == 50
        assert result.overallSummary.commentId == 60

    def test_skips_overall_summary_when_nonzero(self):
        """Does not overwrite overallSummary if threadId is already set."""
        state = _make_review_state(
            overallSummary=OverallSummary(threadId=999, commentId=888),
        )
        threads = [
            _make_thread(
                50,
                60,
                "<!-- agdt-review:v1 type:overall-summary pr:100 -->\nNew overall",
            ),
        ]
        result = sync_review_state_from_threads(100, threads, state)
        assert result.overallSummary.threadId == 999  # Not overwritten

    def test_empty_threads_no_change(self):
        """Empty thread list causes no changes."""
        state = _make_review_state()
        result = sync_review_state_from_threads(100, [], state)
        assert result.files == {}

    def test_threads_without_markers_ignored(self):
        """Threads without markers are ignored."""
        threads = [_make_thread(1, 2, "Just a human comment")]
        state = _make_review_state()
        result = sync_review_state_from_threads(100, threads, state)
        assert result.files == {}

    def test_handles_none_in_threads(self):
        """Handles None entries in thread list gracefully."""
        threads = [
            None,
            _make_thread(
                10,
                20,
                "<!-- agdt-review:v1 type:file-summary file:/test.py pr:100 -->",
            ),
        ]
        state = _make_review_state()
        result = sync_review_state_from_threads(100, threads, state)
        assert "/test.py" in result.files

    def test_root_folder_for_top_level_file(self):
        """Files without a folder get 'root' as the folder."""
        threads = [
            _make_thread(
                10,
                20,
                "<!-- agdt-review:v1 type:file-summary file:/README.md pr:100 -->",
            ),
        ]
        state = _make_review_state()
        result = sync_review_state_from_threads(100, threads, state)
        assert result.files["/README.md"].folder == "root"

    def test_skips_thread_without_comments(self):
        """Skips threads that have no comments list."""
        threads = [{"id": 1}]
        state = _make_review_state()
        result = sync_review_state_from_threads(100, threads, state)
        assert result.files == {}

    def test_skips_non_dict_first_comment(self):
        """Skips threads whose first comment is not a dict."""
        threads = [{"id": 1, "comments": ["not a dict"]}]
        state = _make_review_state()
        result = sync_review_state_from_threads(100, threads, state)
        assert result.files == {}

    def test_skips_file_summary_without_file_key(self):
        """Skips file-summary markers that are missing the file key."""
        threads = [
            _make_thread(
                10,
                20,
                "<!-- agdt-review:v1 type:file-summary pr:100 -->",
            ),
        ]
        state = _make_review_state()
        result = sync_review_state_from_threads(100, threads, state)
        assert result.files == {}

    def test_skips_thread_with_mismatched_pr(self):
        """Skips threads whose marker pr value does not match pull_request_id."""
        threads = [
            _make_thread(
                10,
                20,
                "<!-- agdt-review:v1 type:file-summary file:/src/app.ts pr:999 -->",
            ),
        ]
        state = _make_review_state()
        result = sync_review_state_from_threads(100, threads, state)
        assert result.files == {}

    def test_accepts_thread_without_pr_in_marker(self):
        """Accepts threads whose marker has no pr key (backwards compat)."""
        threads = [
            _make_thread(
                10,
                20,
                "<!-- agdt-review:v1 type:file-summary file:/src/app.ts -->",
            ),
        ]
        state = _make_review_state()
        result = sync_review_state_from_threads(100, threads, state)
        assert "/src/app.ts" in result.files

    def test_skips_unsupported_marker_version(self):
        """Skips threads with a marker version other than 1."""
        threads = [
            _make_thread(
                10,
                20,
                "<!-- agdt-review:v99 type:file-summary file:/src/app.ts pr:100 -->",
            ),
        ]
        state = _make_review_state()
        result = sync_review_state_from_threads(100, threads, state)
        assert result.files == {}

    def test_skips_unrecognised_marker_type(self):
        """Skips threads whose marker type is not in MARKER_TYPES."""
        threads = [
            _make_thread(
                10,
                20,
                "<!-- agdt-review:v1 type:unknown-type file:/src/app.ts pr:100 -->",
            ),
        ]
        state = _make_review_state()
        result = sync_review_state_from_threads(100, threads, state)
        assert result.files == {}

    def test_handles_url_encoded_file_path(self):
        """Correctly processes URL-encoded file paths from markers."""
        threads = [
            _make_thread(
                10,
                20,
                "<!-- agdt-review:v1 type:file-summary file:/src/my%20file.ts pr:100 -->",
            ),
        ]
        state = _make_review_state()
        result = sync_review_state_from_threads(100, threads, state)
        assert "/src/my file.ts" in result.files

    def test_skips_deleted_thread(self):
        """Skips threads where isDeleted is True."""
        threads = [
            {
                "id": 10,
                "isDeleted": True,
                "comments": [
                    {
                        "id": 20,
                        "content": "<!-- agdt-review:v1 type:file-summary file:/src/app.ts pr:100 -->",
                    }
                ],
            },
        ]
        state = _make_review_state()
        result = sync_review_state_from_threads(100, threads, state)
        assert result.files == {}

    def test_skips_thread_with_deleted_first_comment(self):
        """Skips threads whose first comment has isDeleted True."""
        threads = [
            {
                "id": 10,
                "comments": [
                    {
                        "id": 20,
                        "isDeleted": True,
                        "content": "<!-- agdt-review:v1 type:file-summary file:/src/app.ts pr:100 -->",
                    }
                ],
            },
        ]
        state = _make_review_state()
        result = sync_review_state_from_threads(100, threads, state)
        assert result.files == {}

    def test_ignores_recognised_non_handled_marker_type(self):
        """Ignores threads with a valid marker type that has no handler (e.g., activity-log)."""
        threads = [
            _make_thread(
                10,
                20,
                "<!-- agdt-review:v1 type:activity-log file:/src/app.ts pr:100 -->",
            ),
        ]
        state = _make_review_state()
        result = sync_review_state_from_threads(100, threads, state)
        # activity-log is in MARKER_TYPES but has no handler in sync_review_state_from_threads
        assert result.files == {}
        assert result.overallSummary.threadId == 0
