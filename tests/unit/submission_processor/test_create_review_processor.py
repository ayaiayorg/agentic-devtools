"""Tests for agentic_devtools.submission_processor.create_review_processor."""

from unittest.mock import MagicMock, patch

from agentic_devtools.submission_processor import create_review_processor

from .conftest import REPO_ID, make_item


class TestCreateReviewProcessor:
    """Tests for create_review_processor factory function."""

    @patch("agentic_devtools.submission_processor.process_submission")
    def test_returns_callable_that_invokes_process_submission(self, mock_process, config):
        """Verify create_review_processor returns a callable that invokes process_submission."""
        headers = {"Auth": "x"}
        mock_requests = MagicMock()

        processor = create_review_processor(config, headers, REPO_ID, requests_module=mock_requests)
        assert callable(processor)

        item = make_item()
        processor(item)

        mock_process.assert_called_once_with(item, config, headers, REPO_ID, requests_module=mock_requests)
