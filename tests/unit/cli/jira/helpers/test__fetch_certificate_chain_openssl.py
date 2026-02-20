"""
Tests for Jira helper utilities.
"""

from unittest.mock import MagicMock, patch

from agdt_ai_helpers.cli.jira import helpers as jira_helpers


class TestFetchCertificateChainOpenssl:
    """Tests for _fetch_certificate_chain_openssl helper."""

    def test_returns_certificates_on_success(self):
        """Test returns PEM certificates when openssl succeeds."""
        mock_output = b"""
CONNECTED(00000003)
depth=2 C = CH, O = SWICA, CN = SWICA Root CA
verify error:num=19:self signed certificate in certificate chain
---
Certificate chain
 0 s:C = CH, ST = Zurich, L = Winterthur, O = SWICA, OU = IT, CN = jira.swica.ch
   i:C = CH, O = SWICA, CN = SWICA Server CA 2
-----BEGIN CERTIFICATE-----
MIIFakeServerCert123
-----END CERTIFICATE-----
 1 s:C = CH, O = SWICA, CN = SWICA Server CA 2
   i:C = CH, O = SWICA, CN = SWICA Root CA
-----BEGIN CERTIFICATE-----
MIIFakeIntermediateCert456
-----END CERTIFICATE-----
---
"""
        with patch("agdt_ai_helpers.cli.subprocess_utils.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=mock_output)
            result = jira_helpers._fetch_certificate_chain_openssl("jira.swica.ch")

        assert result is not None
        assert "-----BEGIN CERTIFICATE-----" in result
        assert "-----END CERTIFICATE-----" in result

    def test_returns_none_on_timeout(self):
        """Test returns None when subprocess times out."""
        import subprocess

        with patch("agdt_ai_helpers.cli.subprocess_utils.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="openssl", timeout=10)
            result = jira_helpers._fetch_certificate_chain_openssl("jira.swica.ch")

        assert result is None

    def test_returns_none_on_file_not_found(self):
        """Test returns None when openssl is not installed."""
        with patch("agdt_ai_helpers.cli.subprocess_utils.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("openssl not found")
            result = jira_helpers._fetch_certificate_chain_openssl("jira.swica.ch")

        assert result is None

    def test_returns_none_on_no_certificates(self):
        """Test returns None when output has no certificates."""
        with patch("agdt_ai_helpers.cli.subprocess_utils.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=b"CONNECTED\n---\nNo certificates\n---")
            result = jira_helpers._fetch_certificate_chain_openssl("jira.swica.ch")

        assert result is None

