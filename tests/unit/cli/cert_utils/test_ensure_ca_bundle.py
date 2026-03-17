"""Tests for ensure_ca_bundle."""

import os
from pathlib import Path
from unittest.mock import patch

from agentic_devtools.cli import cert_utils


class TestEnsureCaBundle:
    """Tests for ensure_ca_bundle."""

    def test_returns_cached_path_when_complete_chain_exists(self, tmp_path):
        """Returns existing cache file path when it contains a complete chain."""
        complete_chain = (
            "-----BEGIN CERTIFICATE-----\nserver\n-----END CERTIFICATE-----\n"
            "-----BEGIN CERTIFICATE-----\nca\n-----END CERTIFICATE-----"
        )
        cache_file = tmp_path / "example.com.pem"
        cache_file.write_text(complete_chain, encoding="utf-8")

        result = cert_utils.ensure_ca_bundle("example.com", cache_file=cache_file)

        assert result == str(cache_file)

    def test_fetches_and_saves_when_cache_missing(self, tmp_path):
        """Fetches and saves the cert chain when no cache file exists."""
        complete_chain = (
            "-----BEGIN CERTIFICATE-----\nserver\n-----END CERTIFICATE-----\n"
            "-----BEGIN CERTIFICATE-----\nca\n-----END CERTIFICATE-----"
        )
        cache_file = tmp_path / "example.com.pem"

        with patch.object(cert_utils, "fetch_certificate_chain_openssl", return_value=complete_chain):
            result = cert_utils.ensure_ca_bundle("example.com", cache_file=cache_file)

        assert result == str(cache_file)
        assert cache_file.read_text(encoding="utf-8") == complete_chain

    def test_refetches_when_cached_single_cert(self, tmp_path):
        """Re-fetches when cached file contains only one certificate (leaf-only is invalid)."""
        single_cert = "-----BEGIN CERTIFICATE-----\nserver\n-----END CERTIFICATE-----"
        cache_file = tmp_path / "example.com.pem"
        cache_file.write_text(single_cert, encoding="utf-8")

        with patch.object(cert_utils, "fetch_certificate_chain_openssl", return_value=None) as mock_openssl:
            with patch.object(cert_utils, "fetch_certificate_chain_ssl", return_value=None):
                result = cert_utils.ensure_ca_bundle("example.com", cache_file=cache_file)

        mock_openssl.assert_called_once()
        assert result is None

    def test_does_not_cache_leaf_only_from_ssl_fallback(self, tmp_path):
        """Does not cache and returns None when openssl fails and ssl returns single cert."""
        single_cert = "-----BEGIN CERTIFICATE-----\nserver\n-----END CERTIFICATE-----"
        cache_file = tmp_path / "example.com.pem"

        with patch.object(cert_utils, "fetch_certificate_chain_openssl", return_value=None):
            with patch.object(cert_utils, "fetch_certificate_chain_ssl", return_value=single_cert):
                result = cert_utils.ensure_ca_bundle("example.com", cache_file=cache_file)

        assert result is None
        assert not cache_file.exists()

    def test_returns_none_when_all_methods_fail(self, tmp_path):
        """Returns None when both openssl and ssl fallback fail."""
        cache_file = tmp_path / "example.com.pem"

        with patch.object(cert_utils, "fetch_certificate_chain_openssl", return_value=None):
            with patch.object(cert_utils, "fetch_certificate_chain_ssl", return_value=None):
                result = cert_utils.ensure_ca_bundle("example.com", cache_file=cache_file)

        assert result is None
        assert not cache_file.exists()

    def test_uses_default_certs_dir_when_no_cache_file_given(self, tmp_path):
        """Uses ~/.agdt/certs/<hostname>.pem as default cache location."""
        complete_chain = (
            "-----BEGIN CERTIFICATE-----\nserver\n-----END CERTIFICATE-----\n"
            "-----BEGIN CERTIFICATE-----\nca\n-----END CERTIFICATE-----"
        )
        with patch.object(cert_utils, "_CERTS_DIR", tmp_path / "certs"):
            with patch.object(cert_utils, "fetch_certificate_chain_openssl", return_value=complete_chain):
                result = cert_utils.ensure_ca_bundle("example.com")

        expected = str(tmp_path / "certs" / "example.com.pem")
        assert result == expected
        assert Path(expected).read_text(encoding="utf-8") == complete_chain

    def test_sanitizes_hostname_with_path_separators(self, tmp_path):
        """Sanitizes hostname containing path separators to prevent traversal."""
        complete_chain = (
            "-----BEGIN CERTIFICATE-----\nserver\n-----END CERTIFICATE-----\n"
            "-----BEGIN CERTIFICATE-----\nca\n-----END CERTIFICATE-----"
        )
        with patch.object(cert_utils, "_CERTS_DIR", tmp_path / "certs"):
            with patch.object(cert_utils, "fetch_certificate_chain_openssl", return_value=complete_chain):
                result = cert_utils.ensure_ca_bundle("../../../etc/passwd")

        result_path = Path(result)
        certs_dir = (tmp_path / "certs").resolve()
        # Must stay inside _CERTS_DIR — no path traversal
        assert str(result_path).startswith(str(certs_dir))
        assert result_path.parent == certs_dir

    def test_ssl_fallback_not_called_when_openssl_returns_incomplete_chain(self, tmp_path, capsys):
        """ssl fallback is NOT called when openssl returns content (even incomplete)."""
        single_cert = "-----BEGIN CERTIFICATE-----\nonly_server\n-----END CERTIFICATE-----"
        cache_file = tmp_path / "example.com.pem"

        with patch.object(cert_utils, "fetch_certificate_chain_openssl", return_value=single_cert) as mock_openssl:
            with patch.object(cert_utils, "fetch_certificate_chain_ssl") as mock_ssl:
                result = cert_utils.ensure_ca_bundle("example.com", cache_file=cache_file)

        mock_openssl.assert_called_once_with("example.com")
        mock_ssl.assert_not_called()
        assert result is None

    def test_refetches_when_cached_file_has_no_certificates(self, tmp_path):
        """Re-fetches when cached file exists but contains no certificates."""
        cache_file = tmp_path / "example.com.pem"
        cache_file.write_text("no certs here", encoding="utf-8")
        complete_chain = (
            "-----BEGIN CERTIFICATE-----\nserver\n-----END CERTIFICATE-----\n"
            "-----BEGIN CERTIFICATE-----\nca\n-----END CERTIFICATE-----"
        )

        with patch.object(cert_utils, "fetch_certificate_chain_openssl", return_value=complete_chain):
            result = cert_utils.ensure_ca_bundle("example.com", cache_file=cache_file)

        assert result == str(cache_file.resolve())
        assert cache_file.read_text(encoding="utf-8") == complete_chain

    def test_refetches_when_cache_file_is_unreadable(self, tmp_path):
        """Re-fetches when cached file exists but is unreadable (OSError)."""
        cache_file = tmp_path / "example.com.pem"
        cache_file.write_text("placeholder", encoding="utf-8")
        complete_chain = (
            "-----BEGIN CERTIFICATE-----\nserver\n-----END CERTIFICATE-----\n"
            "-----BEGIN CERTIFICATE-----\nca\n-----END CERTIFICATE-----"
        )

        def _raise_oserror(*args, **kwargs):
            raise OSError("permission denied")

        with patch.object(cert_utils, "fetch_certificate_chain_openssl", return_value=complete_chain):
            with patch.object(Path, "read_text", _raise_oserror):
                result = cert_utils.ensure_ca_bundle("example.com", cache_file=cache_file)

        assert result == str(cache_file.resolve())

    def test_returns_resolved_absolute_path(self, tmp_path):
        """Returns a resolved absolute path even when cache_file is relative."""
        complete_chain = (
            "-----BEGIN CERTIFICATE-----\nserver\n-----END CERTIFICATE-----\n"
            "-----BEGIN CERTIFICATE-----\nca\n-----END CERTIFICATE-----"
        )
        cache_file = tmp_path / "example.com.pem"

        with patch.object(cert_utils, "fetch_certificate_chain_openssl", return_value=complete_chain):
            result = cert_utils.ensure_ca_bundle("example.com", cache_file=cache_file)

        assert os.path.isabs(result)

    def test_does_not_cache_leaf_only_from_openssl(self, tmp_path):
        """Does not cache and returns None when openssl returns only a leaf cert."""
        single_cert = "-----BEGIN CERTIFICATE-----\nleaf\n-----END CERTIFICATE-----"
        cache_file = tmp_path / "example.com.pem"

        with patch.object(cert_utils, "fetch_certificate_chain_openssl", return_value=single_cert):
            with patch.object(cert_utils, "fetch_certificate_chain_ssl") as mock_ssl:
                result = cert_utils.ensure_ca_bundle("example.com", cache_file=cache_file)

        assert result is None
        assert not cache_file.exists()
        mock_ssl.assert_not_called()

    def test_prints_warning_for_leaf_only_chain_from_openssl(self, tmp_path, capsys):
        """Prints a warning to stderr when only a leaf certificate is available via openssl."""
        single_cert = "-----BEGIN CERTIFICATE-----\nleaf\n-----END CERTIFICATE-----"
        cache_file = tmp_path / "example.com.pem"

        with patch.object(cert_utils, "fetch_certificate_chain_openssl", return_value=single_cert):
            cert_utils.ensure_ca_bundle("example.com", cache_file=cache_file)

        err = capsys.readouterr().err
        assert "Only leaf certificate retrieved for example.com" in err
        assert "chain is incomplete" in err

    def test_prints_warning_for_leaf_only_chain_from_ssl_fallback(self, tmp_path, capsys):
        """Prints a warning to stderr when only a leaf certificate is available via ssl fallback."""
        single_cert = "-----BEGIN CERTIFICATE-----\nleaf\n-----END CERTIFICATE-----"
        cache_file = tmp_path / "example.com.pem"

        with patch.object(cert_utils, "fetch_certificate_chain_openssl", return_value=None):
            with patch.object(cert_utils, "fetch_certificate_chain_ssl", return_value=single_cert):
                cert_utils.ensure_ca_bundle("example.com", cache_file=cache_file)

        err = capsys.readouterr().err
        assert "Only leaf certificate retrieved for example.com" in err
        assert "chain is incomplete" in err
