"""
Tests for Jira helper utilities.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from agdt_ai_helpers.cli.jira import helpers as jira_helpers


class TestEnsureJiraPem:
    """Tests for _ensure_jira_pem helper."""

    def test_returns_existing_pem_path(self):
        """Test returns existing PEM file path without refetching when chain is complete."""
        expected_path = "/fake/path/to/jira_ca_bundle.pem"
        # PEM content with 2 certificates (complete chain)
        complete_chain = (
            "-----BEGIN CERTIFICATE-----\nserver_cert\n-----END CERTIFICATE-----\n"
            "-----BEGIN CERTIFICATE-----\nintermediate_cert\n-----END CERTIFICATE-----"
        )
        with patch("agdt_ai_helpers.cli.jira.helpers._get_temp_jira_pem_path") as mock_path:
            mock_pem = MagicMock(spec=Path)
            mock_pem.exists.return_value = True
            mock_pem.read_text.return_value = complete_chain
            mock_pem.__str__ = MagicMock(return_value=expected_path)
            mock_path.return_value = mock_pem

            result = jira_helpers._ensure_jira_pem("jira.swica.ch")

        assert result == expected_path
        mock_pem.read_text.assert_called_once_with(encoding="utf-8")

    def test_fetches_and_saves_cert_when_not_exists(self):
        """Test fetches certificate and saves when PEM file doesn't exist."""
        mock_cert = "-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----"

        with patch("agdt_ai_helpers.cli.jira.helpers._get_temp_jira_pem_path") as mock_path:
            with patch("agdt_ai_helpers.cli.jira.helpers._fetch_certificate_chain_openssl") as mock_fetch:
                mock_pem = MagicMock(spec=Path)
                mock_pem.exists.return_value = False
                mock_pem.parent.mkdir = MagicMock()
                mock_pem.write_text = MagicMock()
                mock_path.return_value = mock_pem
                mock_fetch.return_value = mock_cert

                result = jira_helpers._ensure_jira_pem("jira.swica.ch")

        mock_pem.write_text.assert_called_once_with(mock_cert, encoding="utf-8")
        assert result == str(mock_pem)

    def test_falls_back_to_ssl_when_openssl_fails(self):
        """Test falls back to ssl module when openssl fails."""
        mock_cert = "-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----"

        with patch("agdt_ai_helpers.cli.jira.helpers._get_temp_jira_pem_path") as mock_path:
            with patch("agdt_ai_helpers.cli.jira.helpers._fetch_certificate_chain_openssl") as mock_openssl:
                with patch("agdt_ai_helpers.cli.jira.helpers._fetch_certificate_chain_ssl") as mock_ssl:
                    mock_pem = MagicMock(spec=Path)
                    mock_pem.exists.return_value = False
                    mock_pem.parent.mkdir = MagicMock()
                    mock_pem.write_text = MagicMock()
                    mock_path.return_value = mock_pem
                    mock_openssl.return_value = None
                    mock_ssl.return_value = mock_cert

                    result = jira_helpers._ensure_jira_pem("jira.swica.ch")

        mock_ssl.assert_called_once()
        assert result == str(mock_pem)

    def test_returns_none_when_all_methods_fail(self):
        """Test returns None when both openssl and ssl module fail."""
        with patch("agdt_ai_helpers.cli.jira.helpers._get_temp_jira_pem_path") as mock_path:
            with patch("agdt_ai_helpers.cli.jira.helpers._fetch_certificate_chain_openssl") as mock_openssl:
                with patch("agdt_ai_helpers.cli.jira.helpers._fetch_certificate_chain_ssl") as mock_ssl:
                    mock_pem = MagicMock(spec=Path)
                    mock_pem.exists.return_value = False
                    mock_path.return_value = mock_pem
                    mock_openssl.return_value = None
                    mock_ssl.return_value = None

                    result = jira_helpers._ensure_jira_pem("jira.swica.ch")

        assert result is None

    def test_refetches_when_existing_pem_has_incomplete_chain(self):
        """Test refetches certificate when existing PEM has only server cert (incomplete chain)."""
        expected_path = "/fake/path/to/jira_ca_bundle.pem"
        # Existing PEM with only 1 certificate (incomplete chain)
        incomplete_chain = "-----BEGIN CERTIFICATE-----\nserver_cert_only\n-----END CERTIFICATE-----"
        # New complete chain from openssl
        complete_chain = (
            "-----BEGIN CERTIFICATE-----\nserver_cert\n-----END CERTIFICATE-----\n"
            "-----BEGIN CERTIFICATE-----\nintermediate_cert\n-----END CERTIFICATE-----"
        )

        with patch("agdt_ai_helpers.cli.jira.helpers._get_temp_jira_pem_path") as mock_path:
            with patch("agdt_ai_helpers.cli.jira.helpers._fetch_certificate_chain_openssl") as mock_openssl:
                mock_pem = MagicMock(spec=Path)
                mock_pem.exists.return_value = True
                mock_pem.read_text.return_value = incomplete_chain
                mock_pem.parent.mkdir = MagicMock()
                mock_pem.write_text = MagicMock()
                mock_pem.__str__ = MagicMock(return_value=expected_path)
                mock_path.return_value = mock_pem
                mock_openssl.return_value = complete_chain

                result = jira_helpers._ensure_jira_pem("jira.swica.ch")

        # Should have refetched and saved the complete chain
        mock_openssl.assert_called_once_with("jira.swica.ch")
        mock_pem.write_text.assert_called_once_with(complete_chain, encoding="utf-8")
        assert result == expected_path

    def test_saves_incomplete_chain_when_openssl_returns_single_cert(self):
        """Test saves and returns path when openssl returns only server cert (incomplete chain)."""
        # openssl returns only 1 certificate - not ideal but better than nothing
        incomplete_chain = "-----BEGIN CERTIFICATE-----\nonly_server_cert\n-----END CERTIFICATE-----"

        with patch("agdt_ai_helpers.cli.jira.helpers._get_temp_jira_pem_path") as mock_path:
            with patch("agdt_ai_helpers.cli.jira.helpers._fetch_certificate_chain_openssl") as mock_openssl:
                with patch("agdt_ai_helpers.cli.jira.helpers._fetch_certificate_chain_ssl") as mock_ssl:
                    mock_pem = MagicMock(spec=Path)
                    mock_pem.exists.return_value = False
                    mock_pem.parent.mkdir = MagicMock()
                    mock_pem.write_text = MagicMock()
                    mock_path.return_value = mock_pem
                    mock_openssl.return_value = incomplete_chain  # Only 1 cert

                    result = jira_helpers._ensure_jira_pem("jira.swica.ch")

        # Should save the incomplete chain (better than nothing)
        mock_openssl.assert_called_once()
        mock_ssl.assert_not_called()  # ssl fallback NOT called when openssl returns content
        mock_pem.write_text.assert_called_once_with(incomplete_chain, encoding="utf-8")
        assert result == str(mock_pem)

