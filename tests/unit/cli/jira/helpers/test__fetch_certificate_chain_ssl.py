"""
Tests for Jira helper utilities.
"""

from unittest.mock import MagicMock, patch

from agdt_ai_helpers.cli.jira import helpers as jira_helpers


class TestFetchCertificateChainSsl:
    """Tests for _fetch_certificate_chain_ssl helper."""

    def test_returns_certificate_on_success(self):
        """Test returns PEM certificate when SSL connection succeeds."""
        mock_cert_der = b"mock_der_certificate"
        mock_cert_pem = "-----BEGIN CERTIFICATE-----\nmock\n-----END CERTIFICATE-----"

        with patch("socket.create_connection") as mock_conn:
            with patch("ssl.create_default_context") as mock_ctx:
                with patch("ssl.DER_cert_to_PEM_cert") as mock_convert:
                    mock_sock = MagicMock()
                    mock_ssock = MagicMock()
                    mock_ssock.getpeercert.return_value = mock_cert_der
                    mock_sock.__enter__.return_value = mock_sock
                    mock_ctx.return_value.wrap_socket.return_value.__enter__.return_value = mock_ssock
                    mock_conn.return_value.__enter__.return_value = mock_sock
                    mock_convert.return_value = mock_cert_pem

                    result = jira_helpers._fetch_certificate_chain_ssl("jira.swica.ch")

        assert result == mock_cert_pem

    def test_returns_none_on_connection_error(self):
        """Test returns None when connection fails."""
        with patch("socket.create_connection") as mock_conn:
            mock_conn.side_effect = ConnectionRefusedError()
            result = jira_helpers._fetch_certificate_chain_ssl("jira.swica.ch")

        assert result is None

    def test_returns_none_when_no_cert(self):
        """Test returns None when no certificate is returned."""
        with patch("socket.create_connection") as mock_conn:
            with patch("ssl.create_default_context"):
                mock_sock = MagicMock()
                mock_ssock = MagicMock()
                mock_ssock.getpeercert.return_value = None
                mock_sock.__enter__.return_value = mock_sock
                mock_conn.return_value.__enter__.return_value = mock_sock

                result = jira_helpers._fetch_certificate_chain_ssl("jira.swica.ch")

        assert result is None
