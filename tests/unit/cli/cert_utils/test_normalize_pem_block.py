"""Tests for normalize_pem_block."""

from agentic_devtools.cli.cert_utils import normalize_pem_block


class TestNormalizePemBlock:
    """Tests for normalize_pem_block."""

    def test_removes_blank_lines_from_certificate_body(self):
        """Blank lines inside a PEM certificate body are removed."""
        pem = "-----BEGIN CERTIFICATE-----\nMIIBkTCB+wIJAKl\n\nbase64datahere==\n-----END CERTIFICATE-----"
        result = normalize_pem_block(pem)
        assert result == ("-----BEGIN CERTIFICATE-----\nMIIBkTCB+wIJAKl\nbase64datahere==\n-----END CERTIFICATE-----")

    def test_strips_trailing_whitespace_from_base64_lines(self):
        """Trailing whitespace on base64 data lines is stripped."""
        pem = "-----BEGIN CERTIFICATE-----\nMIIBkTCB+wIJAKl   \nbase64datahere==\t\n-----END CERTIFICATE-----"
        result = normalize_pem_block(pem)
        assert "   " not in result
        assert "\t" not in result
        assert "MIIBkTCB+wIJAKl\n" in result

    def test_strips_leading_whitespace_from_base64_lines(self):
        """Leading whitespace on base64 data lines is stripped."""
        pem = "-----BEGIN CERTIFICATE-----\n  MIIBkTCB+wIJAKl\n\tbase64datahere==\n-----END CERTIFICATE-----"
        result = normalize_pem_block(pem)
        assert "  MIIBk" not in result
        assert "\tbase64" not in result
        assert "MIIBkTCB+wIJAKl\n" in result
        assert "base64datahere==\n" in result

    def test_trims_whitespace_from_marker_lines(self):
        """Whitespace around BEGIN/END marker lines is trimmed (FR-004)."""
        pem = "  -----BEGIN CERTIFICATE-----  \nMIIBkTCB+wIJAKl\nbase64datahere==\n  -----END CERTIFICATE-----  "
        result = normalize_pem_block(pem)
        assert result.startswith("-----BEGIN CERTIFICATE-----\n")
        assert result.endswith("\n-----END CERTIFICATE-----")

    def test_handles_windows_crlf_line_endings(self):
        """Windows \\r\\n line endings are converted to Unix \\n."""
        pem = "-----BEGIN CERTIFICATE-----\r\nMIIBkTCB+wIJAKl\r\nbase64datahere==\r\n-----END CERTIFICATE-----"
        result = normalize_pem_block(pem)
        assert "\r" not in result
        assert result == ("-----BEGIN CERTIFICATE-----\nMIIBkTCB+wIJAKl\nbase64datahere==\n-----END CERTIFICATE-----")

    def test_removes_whitespace_only_lines(self):
        """Lines containing only whitespace characters (spaces, tabs) are removed."""
        pem = "-----BEGIN CERTIFICATE-----\nMIIBkTCB+wIJAKl\n   \t  \nbase64datahere==\n-----END CERTIFICATE-----"
        result = normalize_pem_block(pem)
        assert result == ("-----BEGIN CERTIFICATE-----\nMIIBkTCB+wIJAKl\nbase64datahere==\n-----END CERTIFICATE-----")

    def test_idempotent_on_valid_pem(self):
        """A well-formed PEM block produces identical output (NFR-003)."""
        pem = "-----BEGIN CERTIFICATE-----\nMIIBkTCB+wIJAKl\nbase64datahere==\n-----END CERTIFICATE-----"
        result = normalize_pem_block(pem)
        assert result == pem
        # Second pass produces same result
        assert normalize_pem_block(result) == pem

    def test_preserves_multiline_base64_content(self):
        """Multi-line base64 content is preserved correctly."""
        pem = (
            "-----BEGIN CERTIFICATE-----\n"
            "MIIEkjCCA3qgAwIBAgIQCgFBQgAAAVOFc2oLheynCDANBgkqhkiG9w0BAQsF\n"
            "ADA/MSQwIgYDVQQKExtEaWdpdGFsIFNpZ25hdHVyZSBUcnVzdCBDby4xFzAV\n"
            "BgNVBAMTDkRTVCBSb290IENBIFgzMB4XDTE2MDMxNzE2NDA0NloXDTIxMDMx\n"
            "-----END CERTIFICATE-----"
        )
        result = normalize_pem_block(pem)
        assert result == pem

    def test_multiple_blank_lines_removed(self):
        """Multiple consecutive blank lines are all removed."""
        pem = "-----BEGIN CERTIFICATE-----\nMIIBkTCB+wIJAKl\n\n\n\nbase64datahere==\n-----END CERTIFICATE-----"
        result = normalize_pem_block(pem)
        assert "\n\n" not in result
        assert "MIIBkTCB+wIJAKl\nbase64datahere==" in result
