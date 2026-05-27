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
        expected_map = {(10, 1): "## Summary"}

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
        expected_map = {(10, 1): "## Expected"}

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
                {(10, 1): "expected"},
                _mock_config(),
                {},
                42,
                "repo-guid",
            )
        assert len(results) == 1
        assert results[0].converged is False

    def test_includes_activity_log_entries(self):
        """Should verify convergence for activity log entries."""
        comment = EligibleComment(
            thread_id=200,
            comment_id=2,
            marker_type="activity-log-entry",
            marker_data={},
            current_content="old log",
        )
        eligible = EligibleComments(activity_log_entries=[comment])

        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"content": "expected log"}
        mock_requests.get.return_value = mock_response

        with patch(
            "agentic_devtools.cli.azure_devops.helpers.require_requests",
            return_value=mock_requests,
        ):
            results = verify_convergence(
                eligible,
                {(200, 2): "expected log"},
                _mock_config(),
                {},
                42,
                "repo-guid",
            )
        assert len(results) == 1
        assert results[0].converged is True

    def test_includes_overall_summary_and_activity_log(self):
        """Should verify all comment types including overall summary."""
        fs = EligibleComment(
            thread_id=10,
            comment_id=1,
            marker_type="file-summary",
            marker_data={},
            current_content="old",
        )
        os_ = EligibleComment(
            thread_id=100,
            comment_id=1,
            marker_type="overall-summary",
            marker_data={},
            current_content="old overall",
        )
        al = EligibleComment(
            thread_id=200,
            comment_id=2,
            marker_type="activity-log-entry",
            marker_data={},
            current_content="old log",
        )
        eligible = EligibleComments(
            file_summaries=[fs],
            overall_summary=os_,
            activity_log_entries=[al],
        )

        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"content": "match"}
        mock_requests.get.return_value = mock_response

        with patch(
            "agentic_devtools.cli.azure_devops.helpers.require_requests",
            return_value=mock_requests,
        ):
            results = verify_convergence(
                eligible,
                {(10, 1): "match", (100, 1): "match", (200, 2): "match"},
                _mock_config(),
                {},
                42,
                "repo-guid",
            )
        assert len(results) == 3
        assert all(r.converged for r in results)
