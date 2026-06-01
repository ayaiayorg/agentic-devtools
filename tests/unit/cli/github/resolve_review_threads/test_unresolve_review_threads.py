"""Tests for agentic_devtools.cli.github.resolve_review_threads.unresolve_review_threads."""

from unittest.mock import patch

from agentic_devtools.cli.github.resolve_review_threads import unresolve_review_threads

_MODULE = "agentic_devtools.cli.github.resolve_review_threads"

_THREADS = [
    {
        "id": "PRT_a",
        "isResolved": True,
        "path": "foo.py",
        "line": 10,
        "startLine": None,
        "isOutdated": False,
        "comments": {
            "nodes": [
                {
                    "databaseId": 101,
                    "body": "fix this",
                    "createdAt": "2026-01-01",
                    "author": {"login": "reviewer"},
                    "commit": {"oid": "abc"},
                }
            ]
        },
    },
    {
        "id": "PRT_b",
        "isResolved": False,
        "path": "bar.py",
        "line": 5,
        "startLine": None,
        "isOutdated": False,
        "comments": {
            "nodes": [
                {
                    "databaseId": 202,
                    "body": "also fix",
                    "createdAt": "2026-01-01",
                    "author": {"login": "reviewer"},
                    "commit": {"oid": "abc"},
                }
            ]
        },
    },
]


class TestUnresolveReviewThreads:
    """Tests for unresolve_review_threads."""

    @patch(f"{_MODULE}._unresolve_thread")
    @patch(f"{_MODULE}._fetch_review_threads")
    def test_unresolves_resolved_thread(self, mock_fetch, mock_unresolve_thread):
        """Thread that is resolved gets unresolved via mutation."""
        mock_fetch.return_value = _THREADS
        mock_unresolve_thread.return_value = True

        result = unresolve_review_threads(42, "owner/repo", comment_ids=[101])

        mock_unresolve_thread.assert_called_once_with("PRT_a")
        assert result["threadsUnresolved"] == 1
        assert result["threadsFailed"] == 0
        assert result["alreadyUnresolved"] == 0
        assert result["verified"] is True

    @patch(f"{_MODULE}._fetch_review_threads")
    def test_skips_already_unresolved_thread(self, mock_fetch):
        """Thread that is already unresolved is marked as already_unresolved."""
        mock_fetch.return_value = _THREADS

        result = unresolve_review_threads(42, "owner/repo", comment_ids=[202])

        assert result["threadsUnresolved"] == 0
        assert result["alreadyUnresolved"] == 1
        assert result["verified"] is True

    @patch(f"{_MODULE}.time.sleep")
    @patch(f"{_MODULE}._unresolve_thread")
    @patch(f"{_MODULE}._fetch_review_threads")
    def test_marks_failed_when_mutation_fails(self, mock_fetch, mock_unresolve_thread, _mock_sleep):
        """Thread where mutation returns False is marked as failed."""
        mock_fetch.return_value = _THREADS
        mock_unresolve_thread.return_value = False

        result = unresolve_review_threads(42, "owner/repo", comment_ids=[101])

        assert result["threadsFailed"] == 1
        assert result["verified"] is False

    @patch(f"{_MODULE}.time.sleep")
    @patch(f"{_MODULE}._unresolve_thread")
    @patch(f"{_MODULE}._fetch_review_threads")
    def test_verification_detects_unresolved_without_retry(self, mock_fetch, mock_unresolve_thread, _mock_sleep):
        """Thread observed unresolved after first attempt is counted as unresolved."""
        mock_fetch.side_effect = [_THREADS, [{**_THREADS[0], "isResolved": False}]]
        mock_unresolve_thread.return_value = False

        result = unresolve_review_threads(42, "owner/repo", comment_ids=[101])

        assert result["threadsUnresolved"] == 1
        assert result["threadsFailed"] == 0
        assert result["verified"] is True
        assert mock_unresolve_thread.call_count == 1
        assert mock_fetch.call_count == 2

    @patch(f"{_MODULE}.time.sleep")
    @patch(f"{_MODULE}._unresolve_thread")
    @patch(f"{_MODULE}._fetch_review_threads")
    def test_retry_when_thread_still_resolved(self, mock_fetch, mock_unresolve_thread, _mock_sleep):
        """Thread still resolved in re-fetch is retried and can succeed."""
        mock_fetch.side_effect = [_THREADS, _THREADS]
        mock_unresolve_thread.side_effect = [False, True]

        result = unresolve_review_threads(42, "owner/repo", comment_ids=[101])

        assert result["threadsUnresolved"] == 1
        assert result["threadsFailed"] == 0
        assert result["verified"] is True
        assert mock_unresolve_thread.call_count == 2
        assert mock_fetch.call_count == 2

    def test_empty_comment_ids_returns_immediately(self):
        """Empty comment_ids returns immediately without fetching."""
        result = unresolve_review_threads(42, "owner/repo", comment_ids=[])

        assert result["totalTargeted"] == 0
        assert result["threadsUnresolved"] == 0
        assert result["verified"] is True
        assert result["prNumber"] == 42
        assert result["repo"] == "owner/repo"
