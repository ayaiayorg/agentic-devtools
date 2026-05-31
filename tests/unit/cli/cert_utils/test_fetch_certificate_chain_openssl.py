"""Tests for fetch_certificate_chain_openssl."""

import subprocess
from unittest.mock import MagicMock, patch

from agentic_devtools.cli import cert_utils


class TestFetchCertificateChainOpenssl:
    """Tests for fetch_certificate_chain_openssl."""

    def test_returns_certificates_on_success(self):
        """Returns PEM certificate chain when openssl succeeds."""
        mock_output = (
            b"---\n"
            b"-----BEGIN CERTIFICATE-----\nMIIFakeServer\n-----END CERTIFICATE-----\n"
            b"-----BEGIN CERTIFICATE-----\nMIIFakeCA\n-----END CERTIFICATE-----\n"
            b"---\n"
        )
        with patch("agentic_devtools.cli.subprocess_utils.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=mock_output)
            result = cert_utils.fetch_certificate_chain_openssl("example.com")

        assert result is not None
        assert "-----BEGIN CERTIFICATE-----" in result
        assert "-----END CERTIFICATE-----" in result

    def test_returns_none_on_timeout(self):
        """Returns None when the openssl subprocess times out."""
        with patch("agentic_devtools.cli.subprocess_utils.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="openssl", timeout=10)
            result = cert_utils.fetch_certificate_chain_openssl("example.com")

        assert result is None

    def test_returns_none_when_openssl_not_found(self):
        """Returns None when openssl is not installed."""
        with patch("agentic_devtools.cli.subprocess_utils.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("openssl not found")
            result = cert_utils.fetch_certificate_chain_openssl("example.com")

        assert result is None

    def test_returns_none_when_no_certificates_in_output(self):
        """Returns None when openssl output contains no certificate blocks."""
        with patch("agentic_devtools.cli.subprocess_utils.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=b"CONNECTED\n---\nNo certs\n---")
            result = cert_utils.fetch_certificate_chain_openssl("example.com")

        assert result is None

    def test_returns_none_on_unexpected_exception(self):
        """Returns None when an unexpected exception occurs."""
        with patch("agentic_devtools.cli.subprocess_utils.subprocess.run") as mock_run:
            mock_run.side_effect = RuntimeError("unexpected")
            result = cert_utils.fetch_certificate_chain_openssl("example.com")

        assert result is None

    def test_normalizes_blank_lines_in_output(self):
        """Blank lines within certificate bodies are removed from output (FR-002)."""
        mock_output = (
            b"---\n"
            b"-----BEGIN CERTIFICATE-----\nMIIFakeServer\n\nMoreData\n-----END CERTIFICATE-----\n"
            b"-----BEGIN CERTIFICATE-----\nMIIFakeCA\n\n-----END CERTIFICATE-----\n"
            b"---\n"
        )
        with patch("agentic_devtools.cli.subprocess_utils.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=mock_output)
            result = cert_utils.fetch_certificate_chain_openssl("example.com")

        assert result is not None
        # No blank lines should exist within cert blocks
        assert "MIIFakeServer\nMoreData" in result
        assert "\n\n" not in result

    def test_handles_whitespace_around_markers(self):
        """Whitespace around BEGIN/END markers is tolerated and trimmed (FR-004)."""
        mock_output = (
            b"---\n"
            b"  -----BEGIN CERTIFICATE-----  \nMIIFakeServer\n  -----END CERTIFICATE-----  \n"
            b"  -----BEGIN CERTIFICATE-----  \nMIIFakeCA\n  -----END CERTIFICATE-----  \n"
            b"---\n"
        )
        with patch("agentic_devtools.cli.subprocess_utils.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=mock_output)
            result = cert_utils.fetch_certificate_chain_openssl("example.com")

        assert result is not None
        # Markers must be canonical (no surrounding whitespace)
        assert "  -----BEGIN" not in result
        assert "-----BEGIN CERTIFICATE-----\nMIIFakeServer" in result
