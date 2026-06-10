"""Tests for _resolve_thread_for_comment."""

import json
from unittest.mock import MagicMock, patch

from agentic_devtools.cli.github.apply_thread_autofix import _resolve_thread_for_comment

_MODULE = "agentic_devtools.cli.github.apply_thread_autofix"


def _make_threads_page(
    comment_id: int,
    thread_id: str = "T_123",
    is_resolved: bool = False,
    has_next_page: bool = False,
    end_cursor: str | None = None,
) -> str:
    """Build a paginated GraphQL threads response."""
    return json.dumps(
        {
            "data": {
                "repository": {
                    "pullRequest": {
                        "reviewThreads": {
                            "pageInfo": {
                                "hasNextPage": has_next_page,
                                "endCursor": end_cursor,
                            },
                            "nodes": [
                                {
                                    "id": thread_id,
                                    "isResolved": is_resolved,
                                    "comments": {"nodes": [{"databaseId": comment_id}]},
                                }
                            ],
                        }
                    }
                }
            }
        }
    )


def _make_empty_threads_page(has_next_page: bool = False, end_cursor: str | None = None) -> str:
    """Build a paginated GraphQL threads response with no nodes."""
    return json.dumps(
        {
            "data": {
                "repository": {
                    "pullRequest": {
                        "reviewThreads": {
                            "pageInfo": {
                                "hasNextPage": has_next_page,
                                "endCursor": end_cursor,
                            },
                            "nodes": [],
                        }
                    }
                }
            }
        }
    )


class TestResolveThreadForComment:
    """Tests for _resolve_thread_for_comment."""

    @patch(f"{_MODULE}.run_safe")
    def test_successful_resolve(self, mock_run: MagicMock) -> None:
        threads_resp = _make_threads_page(100, "T_abc")
        resolve_resp = json.dumps({"data": {"resolveReviewThread": {"thread": {"id": "T_abc", "isResolved": True}}}})
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=threads_resp, stderr=""),
            MagicMock(returncode=0, stdout=resolve_resp, stderr=""),
        ]

        result = _resolve_thread_for_comment(5, "owner/repo", 100)
        assert result is True

    @patch(f"{_MODULE}.run_safe")
    def test_returns_false_when_threads_fetch_fails(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        result = _resolve_thread_for_comment(5, "owner/repo", 100)
        assert result is False

    @patch(f"{_MODULE}.run_safe")
    def test_returns_false_when_response_parse_fails(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout="not json", stderr="")
        result = _resolve_thread_for_comment(5, "owner/repo", 100)
        assert result is False

    @patch(f"{_MODULE}.run_safe")
    def test_returns_false_when_thread_not_found(self, mock_run: MagicMock) -> None:
        # Thread has a different comment_id, and no next page
        threads_resp = _make_threads_page(999, "T_xyz")
        mock_run.return_value = MagicMock(returncode=0, stdout=threads_resp, stderr="")

        result = _resolve_thread_for_comment(5, "owner/repo", 100)
        assert result is False

    @patch(f"{_MODULE}.run_safe")
    def test_skips_already_resolved_threads(self, mock_run: MagicMock) -> None:
        # Thread containing the comment is already resolved; no next page
        threads_resp = _make_threads_page(100, "T_abc", is_resolved=True)
        mock_run.return_value = MagicMock(returncode=0, stdout=threads_resp, stderr="")

        result = _resolve_thread_for_comment(5, "owner/repo", 100)
        assert result is False

    @patch(f"{_MODULE}.run_safe")
    def test_returns_false_when_resolve_mutation_fails(self, mock_run: MagicMock) -> None:
        threads_resp = _make_threads_page(100, "T_abc")
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=threads_resp, stderr=""),
            MagicMock(returncode=1, stdout="", stderr="mutation failed"),
        ]

        result = _resolve_thread_for_comment(5, "owner/repo", 100)
        assert result is False

    @patch(f"{_MODULE}.run_safe")
    def test_returns_false_on_unexpected_resolve_response(self, mock_run: MagicMock) -> None:
        threads_resp = _make_threads_page(100, "T_abc")
        # The resolve response is valid JSON but missing expected keys
        resolve_resp = json.dumps({"data": {"unexpected": True}})
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=threads_resp, stderr=""),
            MagicMock(returncode=0, stdout=resolve_resp, stderr=""),
        ]

        result = _resolve_thread_for_comment(5, "owner/repo", 100)
        assert result is False

    @patch(f"{_MODULE}.run_safe")
    def test_finds_thread_on_second_page(self, mock_run: MagicMock) -> None:
        """Thread not on first page is found on the second page via pagination."""
        # First page: different comment, has a next page
        page1 = _make_threads_page(999, "T_other", has_next_page=True, end_cursor="cursor_abc")
        # Second page: the target comment, no next page
        page2 = _make_threads_page(100, "T_target")
        resolve_resp = json.dumps({"data": {"resolveReviewThread": {"thread": {"id": "T_target", "isResolved": True}}}})
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=page1, stderr=""),
            MagicMock(returncode=0, stdout=page2, stderr=""),
            MagicMock(returncode=0, stdout=resolve_resp, stderr=""),
        ]

        result = _resolve_thread_for_comment(5, "owner/repo", 100)
        assert result is True
        # Verify the second fetch included the cursor
        second_call_args = mock_run.call_args_list[1]
        assert "-f" in second_call_args[0][0]
        assert any("cursor=cursor_abc" in arg for arg in second_call_args[0][0])

    @patch(f"{_MODULE}.run_safe")
    def test_returns_false_when_thread_missing_across_all_pages(self, mock_run: MagicMock) -> None:
        """If all pages are exhausted without finding the comment, returns False."""
        page1 = _make_empty_threads_page(has_next_page=True, end_cursor="c1")
        page2 = _make_empty_threads_page(has_next_page=False)
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=page1, stderr=""),
            MagicMock(returncode=0, stdout=page2, stderr=""),
        ]

        result = _resolve_thread_for_comment(5, "owner/repo", 100)
        assert result is False

    @patch(f"{_MODULE}.run_safe")
    def test_returns_false_when_second_page_fetch_fails(self, mock_run: MagicMock) -> None:
        """If pagination fetch fails on a subsequent page, returns False."""
        page1 = _make_empty_threads_page(has_next_page=True, end_cursor="c1")
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=page1, stderr=""),
            MagicMock(returncode=1, stdout="", stderr="network error"),
        ]

        result = _resolve_thread_for_comment(5, "owner/repo", 100)
        assert result is False
