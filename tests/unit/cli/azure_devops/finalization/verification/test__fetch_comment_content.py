"""Tests for _fetch_comment_content function."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure_devops.finalization.models import EligibleComment
from agentic_devtools.cli.azure_devops.finalization.verification import _fetch_comment_content


def _mock_config():
    config = MagicMock()
    config.build_api_url.return_value = "https://api/comment"
    return config


class TestFetchCommentContent:
    """Tests for _fetch_comment_content function."""

    def test_returns_content_on_success(self):
        """Should return comment content from API response."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"content": "## File Summary\nApproved"}
        mock_requests.get.return_value = mock_response

        comment = EligibleComment(
            thread_id=10, comment_id=1, marker_type="file-summary",
            marker_data={}, current_content="old",
        )
        with patch(
            "agentic_devtools.cli.azure_devops.helpers.require_requests",
            return_value=mock_requests,
        ):
            result = _fetch_comment_content(_mock_config(), {}, "repo-guid", 42, comment)

        assert result == "## File Summary\nApproved"

    def test_returns_empty_when_no_content_key(self):
        """Should return empty string when API response has no content key."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_requests.get.return_value = mock_response

        comment = EligibleComment(
            thread_id=10, comment_id=1, marker_type="file-summary",
            marker_data={}, current_content="old",
        )
        with patch(
            "agentic_devtools.cli.azure_devops.helpers.require_requests",
            return_value=mock_requests,
        ):
            result = _fetch_comment_content(_mock_config(), {}, "repo-guid", 42, comment)

        assert result == ""

    def test_raises_on_api_error(self):
        """Should propagate exception from API call."""
        mock_requests = MagicMock()
        mock_requests.get.side_effect = Exception("connection error")

        comment = EligibleComment(
            thread_id=10, comment_id=1, marker_type="file-summary",
            marker_data={}, current_content="old",
        )
        try:
            with patch(
                "agentic_devtools.cli.azure_devops.helpers.require_requests",
                return_value=mock_requests,
            ):
                _fetch_comment_content(_mock_config(), {}, "repo-guid", 42, comment)
            assert False, "Should have raised"
        except Exception as exc:
            assert "connection error" in str(exc)

    def test_builds_correct_url(self):
        """Should build API URL with thread and comment IDs."""
        config = _mock_config()
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"content": "data"}
        mock_requests.get.return_value = mock_response

        comment = EligibleComment(
            thread_id=10, comment_id=5, marker_type="file-summary",
            marker_data={}, current_content="old",
        )
        with patch(
            "agentic_devtools.cli.azure_devops.helpers.require_requests",
            return_value=mock_requests,
        ):
            _fetch_comment_content(config, {}, "repo-guid", 42, comment)

        config.build_api_url.assert_called_once_with(
            "repo-guid", "pullRequests", 42, "threads", 10, "comments", 5,
        )
