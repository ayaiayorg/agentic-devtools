"""Tests for count_certificates_in_pem."""

from agentic_devtools.cli import cert_utils


class TestCountCertificatesInPem:
    """Tests for count_certificates_in_pem."""

    def test_returns_zero_for_empty_string(self):
        """Returns 0 for an empty string."""
        assert cert_utils.count_certificates_in_pem("") == 0

    def test_returns_one_for_single_cert(self):
        """Returns 1 when there is one certificate block."""
        pem = "-----BEGIN CERTIFICATE-----\ndata\n-----END CERTIFICATE-----"
        assert cert_utils.count_certificates_in_pem(pem) == 1

    def test_returns_two_for_full_chain(self):
        """Returns 2 for a two-certificate chain."""
        pem = (
            "-----BEGIN CERTIFICATE-----\nserver\n-----END CERTIFICATE-----\n"
            "-----BEGIN CERTIFICATE-----\nca\n-----END CERTIFICATE-----"
        )
        assert cert_utils.count_certificates_in_pem(pem) == 2

    def test_returns_three_for_three_certs(self):
        """Returns 3 for a three-certificate chain."""
        block = "-----BEGIN CERTIFICATE-----\ndata\n-----END CERTIFICATE-----\n"
        assert cert_utils.count_certificates_in_pem(block * 3) == 3
