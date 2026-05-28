"""Tests for normalize_pem."""

from agentic_devtools.cli import cert_utils


class TestNormalizePem:
    """Tests for normalize_pem."""

    def test_returns_input_unchanged_when_no_certificates(self):
        """Returns the input string unchanged when no PEM certificate blocks are found."""
        content = "not a certificate"
        assert cert_utils.normalize_pem(content) == content

    def test_returns_empty_string_unchanged(self):
        """Returns an empty string unchanged."""
        assert cert_utils.normalize_pem("") == ""

    def test_valid_pem_without_blank_lines_is_unchanged(self):
        """A well-formed PEM block with no blank lines is returned unchanged."""
        pem = (
            "-----BEGIN CERTIFICATE-----\n"
            "MIIB1TCCAb2gAwIBAgIJAKl\n"
            "base64datahere==\n"
            "-----END CERTIFICATE-----"
        )
        assert cert_utils.normalize_pem(pem) == pem

    def test_blank_lines_inside_certificate_body_are_removed(self):
        """Blank lines inside a PEM certificate body are stripped."""
        pem_with_blanks = (
            "-----BEGIN CERTIFICATE-----\n"
            "MIIB1TCCAb2g\n"
            "\n"
            "base64datahere==\n"
            "\n"
            "-----END CERTIFICATE-----"
        )
        expected = (
            "-----BEGIN CERTIFICATE-----\n"
            "MIIB1TCCAb2g\n"
            "base64datahere==\n"
            "-----END CERTIFICATE-----"
        )
        assert cert_utils.normalize_pem(pem_with_blanks) == expected

    def test_multiple_certificates_are_each_normalized(self):
        """Blank lines are removed from each certificate block in a multi-cert PEM."""
        pem = (
            "-----BEGIN CERTIFICATE-----\n"
            "cert1line1\n"
            "\n"
            "cert1line2\n"
            "-----END CERTIFICATE-----\n"
            "-----BEGIN CERTIFICATE-----\n"
            "cert2line1\n"
            "\n"
            "cert2line2\n"
            "-----END CERTIFICATE-----"
        )
        result = cert_utils.normalize_pem(pem)
        # Both certs should be normalized: no blank lines within their bodies
        assert "\n\n" not in result
        assert "cert1line1\ncert1line2" in result
        assert "cert2line1\ncert2line2" in result

    def test_whitespace_only_lines_inside_body_are_removed(self):
        """Lines containing only whitespace inside a certificate body are removed."""
        pem_with_whitespace = (
            "-----BEGIN CERTIFICATE-----\n"
            "base64data\n"
            "   \n"
            "moredata==\n"
            "-----END CERTIFICATE-----"
        )
        expected = (
            "-----BEGIN CERTIFICATE-----\n"
            "base64data\n"
            "moredata==\n"
            "-----END CERTIFICATE-----"
        )
        assert cert_utils.normalize_pem(pem_with_whitespace) == expected
