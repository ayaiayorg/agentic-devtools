"""Tests for _fetch_review_threads helper (GraphQL cursor pagination)."""

import json
import subprocess
from unittest.mock import patch

import pytest

from agentic_devtools.cli.github.resolve_review_threads import (
    _fetch_review_threads,
)

_MODULE = "agentic_devtools.cli.github.resolve_review_threads"


def _graphql_page(nodes, has_next=False, end_cursor=None):
    """Build a mock GraphQL response page."""
    return json.dumps(
        {
            "data": {
                "repository": {
                    "pullRequest": {
                        "reviewThreads": {
                            "pageInfo": {
                                "hasNextPage": has_next,
                                "endCursor": end_cursor,
                            },
                            "nodes": nodes,
                        }
                    }
                }
            }
        }
    )


_THREAD_A = {
    "id": "PRT_aaa",
    "isResolved": False,
    "comments": {"nodes": [{"databaseId": 100}]},
}
_THREAD_B = {
    "id": "PRT_bbb",
    "isResolved": True,
    "comments": {"nodes": [{"databaseId": 200}]},
}
_THREAD_C = {
    "id": "PRT_ccc",
    "isResolved": False,
    "comments": {"nodes": [{"databaseId": 300}]},
}


class TestFetchReviewThreads:
    """Tests for _fetch_review_threads."""

    @patch(f"{_MODULE}.time.sleep")
    @patch(f"{_MODULE}.run_safe")
    def test_single_page(self, mock_run, mock_sleep):
        """Return threads from a single page response."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=_graphql_page([_THREAD_A, _THREAD_B]),
            stderr="",
        )
        result = _fetch_review_threads(1, "owner", "repo")
        assert len(result) == 2
        assert result[0]["id"] == "PRT_aaa"
        assert result[1]["id"] == "PRT_bbb"

    @patch(f"{_MODULE}.time.sleep")
    @patch(f"{_MODULE}.run_safe")
    def test_multi_page_pagination(self, mock_run, mock_sleep):
        """Accumulate threads across multiple pages."""
        mock_run.side_effect = [
            subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout=_graphql_page([_THREAD_A], has_next=True, end_cursor="cursor1"),
                stderr="",
            ),
            subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout=_graphql_page([_THREAD_B, _THREAD_C]),
                stderr="",
            ),
        ]
        result = _fetch_review_threads(1, "owner", "repo")
        assert len(result) == 3
        # Verify cursor was passed on second call
        second_call_args = mock_run.call_args_list[1][0][0]
        assert "threadsCursor=cursor1" in " ".join(second_call_args)

    @patch(f"{_MODULE}.time.sleep")
    @patch(f"{_MODULE}.run_safe")
    def test_retry_on_failure(self, mock_run, mock_sleep):
        """Retry a failed page, then succeed."""
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="err"),
            subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout=_graphql_page([_THREAD_A]),
                stderr="",
            ),
        ]
        result = _fetch_review_threads(1, "owner", "repo")
        assert len(result) == 1
        mock_sleep.assert_called_once()

    @patch(f"{_MODULE}.time.sleep")
    @patch(f"{_MODULE}.run_safe")
    def test_all_retries_exhausted(self, mock_run, mock_sleep):
        """Raise RuntimeError when all page retries fail."""
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="fail")
        with pytest.raises(RuntimeError, match="Failed to fetch review threads"):
            _fetch_review_threads(1, "owner", "repo")
        assert mock_run.call_count == 3

    @patch(f"{_MODULE}.time.sleep")
    @patch(f"{_MODULE}.run_safe")
    def test_malformed_json_retries(self, mock_run, mock_sleep):
        """Retry on malformed JSON, then succeed."""
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0, stdout="not json", stderr=""),
            subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout=_graphql_page([_THREAD_B]),
                stderr="",
            ),
        ]
        result = _fetch_review_threads(1, "owner", "repo")
        assert len(result) == 1

    @patch(f"{_MODULE}.time.sleep")
    @patch(f"{_MODULE}.run_safe")
    def test_missing_end_cursor_raises(self, mock_run, mock_sleep):
        """Raise RuntimeError when hasNextPage=True but endCursor is null."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=_graphql_page([_THREAD_A], has_next=True, end_cursor=None),
            stderr="",
        )
        with pytest.raises(RuntimeError, match="hasNextPage=True but did not provide an endCursor"):
            _fetch_review_threads(1, "owner", "repo")

    @patch(f"{_MODULE}.time.sleep")
    @patch(f"{_MODULE}.run_safe", side_effect=OSError("gh not found"))
    def test_oserror_retries_then_raises(self, mock_run, mock_sleep):
        """Catch OSError from run_safe and retry, then raise RuntimeError."""
        with pytest.raises(RuntimeError, match="Failed to fetch review threads"):
            _fetch_review_threads(1, "owner", "repo")
        assert mock_run.call_count == 3  # 1 initial + 2 retries

    @patch(f"{_MODULE}.time.sleep")
    @patch(f"{_MODULE}.run_safe")
    def test_oserror_then_success(self, mock_run, mock_sleep):
        """Recover from OSError on first attempt when second succeeds."""
        mock_run.side_effect = [
            OSError("permission denied"),
            subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout=_graphql_page([_THREAD_A]),
                stderr="",
            ),
        ]
        result = _fetch_review_threads(1, "owner", "repo")
        assert len(result) == 1
        assert mock_run.call_count == 2
