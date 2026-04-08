"""Tests for _resolve_and_verify orchestration function."""

from unittest.mock import patch

from agentic_devtools.cli.github.resolve_review_threads import _resolve_and_verify

_MODULE = "agentic_devtools.cli.github.resolve_review_threads"


def _thread(thread_id, comment_id, is_resolved):
    return {
        "id": thread_id,
        "isResolved": is_resolved,
        "comments": {"nodes": [{"databaseId": comment_id}]},
    }


class TestResolveAndVerify:
    """Tests for _resolve_and_verify."""

    @patch(f"{_MODULE}._resolve_thread")
    @patch(f"{_MODULE}._fetch_review_threads")
    def test_all_resolve_first_pass(self, mock_fetch, mock_resolve):
        """All threads resolve on first pass → verified=True."""
        mock_fetch.return_value = [
            _thread("PRT_a", 1, False),
            _thread("PRT_b", 2, False),
        ]
        mock_resolve.return_value = True

        result = _resolve_and_verify(42, "owner", "repo", {1, 2})

        assert result["threadsResolved"] == 2
        assert result["threadsFailed"] == 0
        assert result["alreadyResolved"] == 0
        assert result["totalTargeted"] == 2
        assert result["verified"] is True

    @patch(f"{_MODULE}._resolve_thread")
    @patch(f"{_MODULE}._fetch_review_threads")
    def test_all_already_resolved(self, mock_fetch, mock_resolve):
        """All threads already resolved → no mutations fired."""
        mock_fetch.return_value = [
            _thread("PRT_a", 1, True),
            _thread("PRT_b", 2, True),
        ]

        result = _resolve_and_verify(42, "owner", "repo", {1, 2})

        assert result["threadsResolved"] == 0
        assert result["alreadyResolved"] == 2
        assert result["verified"] is True
        mock_resolve.assert_not_called()

    @patch(f"{_MODULE}._resolve_thread")
    @patch(f"{_MODULE}._fetch_review_threads")
    def test_retry_succeeds_on_verification(self, mock_fetch, mock_resolve):
        """One thread fails first pass → retry resolves it → verified=True."""
        # Initial fetch: 2 unresolved threads
        initial_threads = [
            _thread("PRT_a", 1, False),
            _thread("PRT_b", 2, False),
        ]
        # Verification fetch: PRT_b now resolved
        verify_threads = [
            _thread("PRT_a", 1, False),
            _thread("PRT_b", 2, True),
        ]
        mock_fetch.side_effect = [initial_threads, verify_threads]

        # First pass: PRT_a succeeds, PRT_b fails
        # Retry: PRT_a succeeds
        mock_resolve.side_effect = [True, False, True]

        result = _resolve_and_verify(42, "owner", "repo", {1, 2})

        assert result["threadsResolved"] == 2
        assert result["threadsFailed"] == 0
        assert result["verified"] is True

    @patch(f"{_MODULE}._resolve_thread")
    @patch(f"{_MODULE}._fetch_review_threads")
    def test_retry_mutation_succeeds_when_still_unresolved(self, mock_fetch, mock_resolve):
        """Thread still unresolved in re-fetch but retry mutation succeeds."""
        initial_threads = [_thread("PRT_a", 1, False)]
        # Re-fetch still shows unresolved
        verify_threads = [_thread("PRT_a", 1, False)]
        mock_fetch.side_effect = [initial_threads, verify_threads]

        # First resolve fails, retry succeeds
        mock_resolve.side_effect = [False, True]

        result = _resolve_and_verify(42, "owner", "repo", {1}, max_retries=1)

        assert result["threadsResolved"] == 1
        assert result["threadsFailed"] == 0
        assert result["verified"] is True

    @patch(f"{_MODULE}._resolve_thread")
    @patch(f"{_MODULE}._fetch_review_threads")
    def test_all_retries_exhausted(self, mock_fetch, mock_resolve):
        """Thread fails all retries → threadsFailed=1, verified=False."""
        threads = [_thread("PRT_a", 1, False)]
        mock_fetch.return_value = threads
        mock_resolve.return_value = False

        result = _resolve_and_verify(42, "owner", "repo", {1}, max_retries=2)

        assert result["threadsFailed"] == 1
        assert result["verified"] is False
        # Initial resolve + 2 retries = 3 calls
        assert mock_resolve.call_count == 3

    @patch(f"{_MODULE}._resolve_thread")
    @patch(f"{_MODULE}._fetch_review_threads")
    def test_empty_target_no_threads_match(self, mock_fetch, mock_resolve):
        """No threads match target → all counts 0, verified=True."""
        mock_fetch.return_value = [
            _thread("PRT_a", 99, False),
        ]

        result = _resolve_and_verify(42, "owner", "repo", {1})

        assert result["totalTargeted"] == 0
        assert result["verified"] is True
        mock_resolve.assert_not_called()

    @patch(f"{_MODULE}._resolve_thread")
    @patch(f"{_MODULE}._fetch_review_threads")
    def test_mixed_resolved_and_unresolved(self, mock_fetch, mock_resolve):
        """Mix of already-resolved and newly resolved threads."""
        mock_fetch.return_value = [
            _thread("PRT_a", 1, True),  # already resolved
            _thread("PRT_b", 2, False),  # needs resolution
        ]
        mock_resolve.return_value = True

        result = _resolve_and_verify(42, "owner", "repo", {1, 2})

        assert result["alreadyResolved"] == 1
        assert result["threadsResolved"] == 1
        assert result["verified"] is True
