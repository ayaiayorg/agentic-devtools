"""Tests for _print_ssl_error_help."""

from agentic_devtools.cli import cert_utils


class TestPrintSslErrorHelp:
    """Tests for _print_ssl_error_help."""

    def test_prints_hostname_in_error(self, capsys):
        """Includes the failing hostname in the error message."""
        cert_utils._print_ssl_error_help("api.github.com")
        err = capsys.readouterr().err
        assert "SSL verification failed for api.github.com" in err

    def test_suggests_agdt_setup_certs(self, capsys):
        """Suggests running agdt-setup-certs as first resolution step."""
        cert_utils._print_ssl_error_help("api.github.com")
        err = capsys.readouterr().err
        assert "agdt-setup-certs" in err

    def test_suggests_no_verify_ssl(self, capsys):
        """Suggests --no-verify-ssl as a fallback option."""
        cert_utils._print_ssl_error_help("api.github.com")
        err = capsys.readouterr().err
        assert "--no-verify-ssl" in err

    def test_suggests_requests_ca_bundle(self, capsys):
        """Suggests setting REQUESTS_CA_BUNDLE."""
        cert_utils._print_ssl_error_help("example.com")
        err = capsys.readouterr().err
        assert "REQUESTS_CA_BUNDLE" in err
