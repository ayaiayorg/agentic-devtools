"""Tests for _get_jira_ssl_verify function."""

from unittest.mock import patch


class TestGetJiraSslVerify:
    """Tests for _get_jira_ssl_verify."""

    def test_delegates_to_jira_helpers(self):
        """Delegates to _get_ssl_verify from jira.helpers."""
        from agentic_devtools.cli.azure_devops.review_jira import _get_jira_ssl_verify

        with patch("agentic_devtools.cli.jira.helpers._get_ssl_verify", return_value="/path/to/ca.pem") as mock_ssl:
            result = _get_jira_ssl_verify()

        assert result == "/path/to/ca.pem"
        mock_ssl.assert_called_once()

    def test_falls_back_to_true_on_exception(self):
        """Falls back to True (system CA) when helpers module raises an exception."""
        from agentic_devtools.cli.azure_devops.review_jira import _get_jira_ssl_verify

        with patch("agentic_devtools.cli.jira.helpers._get_ssl_verify", side_effect=Exception("import error")):
            result = _get_jira_ssl_verify()

        assert result is True
