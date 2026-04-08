"""Tests for _count_suppressed_comments in copilot_review_status module."""

import json
import subprocess
from unittest.mock import patch

import pytest

from agentic_devtools.cli.github.copilot_review_status import _count_suppressed_comments

MODULE = "agentic_devtools.cli.github.copilot_review_status"


def _graphql_ok(nodes, has_next=False, end_cursor=None):
    """Build a successful GraphQL response."""
    data = {
        "data": {
            "node": {
                "comments": {
                    "pageInfo": {
                        "hasNextPage": has_next,
                        "endCursor": end_cursor,
                    },
                    "nodes": nodes,
                }
            }
        }
    }
    return subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(data), stderr="")


def _fail(stderr: str = "error") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr=stderr)


class TestCountSuppressedComments:
    """Tests for _count_suppressed_comments."""

    @patch(f"{MODULE}.time.sleep")
    @patch(f"{MODULE}.run_safe")
    def test_two_minimized_comments(self, mock_run, mock_sleep):
        """Review with 2 minimized comments returns 2."""
        nodes = [
            {"isMinimized": True},
            {"isMinimized": True},
            {"isMinimized": False},
        ]
        mock_run.return_value = _graphql_ok(nodes)

        result = _count_suppressed_comments("PRR_abc123")

        assert result == 2

    @patch(f"{MODULE}.time.sleep")
    @patch(f"{MODULE}.run_safe")
    def test_zero_comments(self, mock_run, mock_sleep):
        """Review with zero comments returns 0."""
        mock_run.return_value = _graphql_ok([])

        result = _count_suppressed_comments("PRR_abc123")

        assert result == 0

    @patch(f"{MODULE}.time.sleep")
    @patch(f"{MODULE}.run_safe")
    def test_multi_page_pagination(self, mock_run, mock_sleep):
        """Cursor-based pagination accumulates across pages."""
        page1 = _graphql_ok([{"isMinimized": True}], has_next=True, end_cursor="cursor1")
        page2 = _graphql_ok([{"isMinimized": True}, {"isMinimized": False}])
        mock_run.side_effect = [page1, page2]

        result = _count_suppressed_comments("PRR_abc123")

        assert result == 2
        assert mock_run.call_count == 2

    @patch(f"{MODULE}.time.sleep")
    @patch(f"{MODULE}.run_safe")
    def test_all_non_minimized_returns_zero(self, mock_run, mock_sleep):
        """All non-minimized comments returns 0."""
        nodes = [{"isMinimized": False}, {"isMinimized": False}]
        mock_run.return_value = _graphql_ok(nodes)

        result = _count_suppressed_comments("PRR_abc123")

        assert result == 0

    @patch(f"{MODULE}.time.sleep")
    @patch(f"{MODULE}.run_safe")
    def test_retry_then_success(self, mock_run, mock_sleep):
        """Retries on failure and succeeds."""
        mock_run.side_effect = [
            _fail("server error"),
            _graphql_ok([{"isMinimized": True}]),
        ]

        result = _count_suppressed_comments("PRR_abc123")

        assert result == 1
        mock_sleep.assert_called_once_with(10)

    @patch(f"{MODULE}.time.sleep")
    @patch(f"{MODULE}.run_safe")
    def test_all_retries_exhausted_raises(self, mock_run, mock_sleep):
        """All retries exhausted raises RuntimeError."""
        mock_run.return_value = _fail("persistent error")

        with pytest.raises(RuntimeError, match="Failed to fetch suppressed comments"):
            _count_suppressed_comments("PRR_abc123")

    @patch(f"{MODULE}.time.sleep")
    @patch(f"{MODULE}.run_safe")
    def test_node_is_none_returns_zero(self, mock_run, mock_sleep, capsys):
        """data.node is None returns 0 with warning."""
        data = {"data": {"node": None}}
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(data), stderr="")

        result = _count_suppressed_comments("PRR_abc123")

        assert result == 0
        assert "returning the suppressed count accumulated so far" in capsys.readouterr().err

    @patch(f"{MODULE}.time.sleep")
    @patch(f"{MODULE}.run_safe")
    def test_node_missing_comments_returns_zero(self, mock_run, mock_sleep, capsys):
        """data.node without comments field returns 0."""
        data = {"data": {"node": {}}}
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(data), stderr="")

        result = _count_suppressed_comments("PRR_abc123")

        assert result == 0
        assert "returning the suppressed count accumulated so far" in capsys.readouterr().err

    def test_empty_node_id_returns_zero(self):
        """Empty review_node_id returns 0."""
        result = _count_suppressed_comments("")
        assert result == 0

    @patch(f"{MODULE}.time.sleep")
    @patch(f"{MODULE}.run_safe", side_effect=OSError("gh not found"))
    def test_oserror_raises_runtime_error(self, mock_run, mock_sleep):
        """OSError from run_safe (gh not installed) raises RuntimeError."""
        with pytest.raises(RuntimeError, match="Failed to fetch suppressed comments"):
            _count_suppressed_comments("PRR_abc123")

    @patch(f"{MODULE}.time.sleep")
    @patch(f"{MODULE}.run_safe")
    def test_missing_end_cursor_raises(self, mock_run, mock_sleep):
        """hasNextPage=true but missing endCursor raises RuntimeError."""
        data = {
            "data": {
                "node": {
                    "comments": {
                        "pageInfo": {"hasNextPage": True, "endCursor": None},
                        "nodes": [{"isMinimized": True}],
                    }
                }
            }
        }
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(data), stderr="")

        with pytest.raises(RuntimeError, match="pageInfo.endCursor was missing or null"):
            _count_suppressed_comments("PRR_abc123")

    @patch(f"{MODULE}.time.sleep")
    @patch(f"{MODULE}.run_safe")
    def test_invalid_json_raises_runtime_error(self, mock_run, mock_sleep):
        """Invalid JSON in GraphQL response raises RuntimeError."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="not valid json", stderr=""
        )

        with pytest.raises(RuntimeError, match="Failed to parse GraphQL response"):
            _count_suppressed_comments("PRR_abc123")
