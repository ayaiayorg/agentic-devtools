"""Tests for verify_convergence function."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure_devops.finalization.models import EligibleComment, EligibleComments
from agentic_devtools.cli.azure_devops.finalization.verification import verify_convergence


def _mock_config():
    config = MagicMock()
    config.build_api_url.return_value = "https://api/url"
    return config


class TestVerifyConvergence:
    """Tests for verify_convergence function."""

    def test_all_converged(self):
        """Should return all converged when API content matches expected."""
        comment = EligibleComment(
            thread_id=10,
            comment_id=1,
            marker_type="file-summary",
            marker_data={},
            current_content="old",
        )
        eligible = EligibleComments(file_summaries=[comment])
        expected_map = {1: "## Summary"}

        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"content": "## Summary"}
        mock_requests.get.return_value = mock_response

        with patch(
            "agentic_devtools.cli.azure_devops.helpers.require_requests",
            return_value=mock_requests,
        ):
            results = verify_convergence(
                eligible,
                expected_map,
                _mock_config(),
                {},
                42,
                "repo-guid",
            )
        assert len(results) == 1
        assert results[0].converged is True

    def test_partial_convergence(self):
        """Should detect non-converged comments."""
        comment = EligibleComment(
            thread_id=10,
            comment_id=1,
            marker_type="file-summary",
            marker_data={},
            current_content="old",
        )
        eligible = EligibleComments(file_summaries=[comment])
        expected_map = {1: "## Expected"}

        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"content": "## Different"}
        mock_requests.get.return_value = mock_response

        with patch(
            "agentic_devtools.cli.azure_devops.helpers.require_requests",
            return_value=mock_requests,
        ):
            results = verify_convergence(
                eligible,
                expected_map,
                _mock_config(),
                {},
                42,
                "repo-guid",
            )
        assert len(results) == 1
        assert results[0].converged is False

    def test_handles_api_error(self):
        """Should treat API errors as non-converged."""
        comment = EligibleComment(
            thread_id=10,
            comment_id=1,
            marker_type="file-summary",
            marker_data={},
            current_content="old",
        )
        eligible = EligibleComments(file_summaries=[comment])

        mock_requests = MagicMock()
        mock_requests.get.side_effect = Exception("API error")

        with patch(
            "agentic_devtools.cli.azure_devops.helpers.require_requests",
            return_value=mock_requests,
        ):
            results = verify_convergence(
                eligible,
                {1: "expected"},
                _mock_config(),
                {},
                42,
                "repo-guid",
            )
        assert len(results) == 1
        assert results[0].converged is False
