"""
Tests for Jira helper utilities.
"""


from agdt_ai_helpers.cli.jira import helpers as jira_helpers


class TestCountCertificatesInPem:
    """Tests for _count_certificates_in_pem helper."""

    def test_counts_zero_certificates_in_empty_string(self):
        """Test returns 0 for empty string."""
        assert jira_helpers._count_certificates_in_pem("") == 0

    def test_counts_single_certificate(self):
        """Test counts a single certificate correctly."""
        pem_content = "-----BEGIN CERTIFICATE-----\nMIIFake\n-----END CERTIFICATE-----"
        assert jira_helpers._count_certificates_in_pem(pem_content) == 1

    def test_counts_multiple_certificates(self):
        """Test counts multiple certificates correctly."""
        pem_content = (
            "-----BEGIN CERTIFICATE-----\nserver_cert\n-----END CERTIFICATE-----\n"
            "-----BEGIN CERTIFICATE-----\nintermediate_cert\n-----END CERTIFICATE-----\n"
            "-----BEGIN CERTIFICATE-----\nroot_cert\n-----END CERTIFICATE-----"
        )
        assert jira_helpers._count_certificates_in_pem(pem_content) == 3

    def test_counts_certificates_with_extra_text(self):
        """Test counts certificates even with additional text between them."""
        pem_content = (
            "Certificate chain:\n"
            "-----BEGIN CERTIFICATE-----\ncert1\n-----END CERTIFICATE-----\n"
            "some info\n"
            "-----BEGIN CERTIFICATE-----\ncert2\n-----END CERTIFICATE-----"
        )
        assert jira_helpers._count_certificates_in_pem(pem_content) == 2

