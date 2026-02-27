"""Tests for get_ssl_verify."""

from unittest.mock import patch

import pytest

from agentic_devtools.cli import cert_utils


class TestGetSslVerify:
    """Tests for get_ssl_verify."""

    def test_returns_requests_ca_bundle_env_var(self, tmp_path):
        """Returns REQUESTS_CA_BUNDLE env var path when it exists."""
        ca_path = str(tmp_path / "ca.pem")
        (tmp_path / "ca.pem").write_text("cert", encoding="utf-8")

        with patch.dict("os.environ", {"REQUESTS_CA_BUNDLE": ca_path}, clear=True):
            result = cert_utils.get_ssl_verify("example.com")

        assert result == ca_path

    def test_ignores_requests_ca_bundle_when_file_missing(self):
        """Ignores REQUESTS_CA_BUNDLE when the file does not exist."""
        with patch.dict("os.environ", {"REQUESTS_CA_BUNDLE": "/nonexistent/ca.pem"}, clear=True):
            with patch.object(cert_utils, "ensure_ca_bundle", return_value=None):
                result = cert_utils.get_ssl_verify("example.com")

        assert result is True

    def test_returns_cached_pem_path_when_available(self, tmp_path):
        """Returns cached PEM path from ensure_ca_bundle when available."""
        pem_path = str(tmp_path / "example.com.pem")

        with patch.dict("os.environ", {}, clear=True):
            with patch.object(cert_utils, "ensure_ca_bundle", return_value=pem_path):
                result = cert_utils.get_ssl_verify("example.com")

        assert result == pem_path

    def test_returns_true_when_no_cert_available(self):
        """Returns True (system CA) when no CA bundle can be fetched."""
        with patch.dict("os.environ", {}, clear=True):
            with patch.object(cert_utils, "ensure_ca_bundle", return_value=None):
                result = cert_utils.get_ssl_verify("example.com")

        assert result is True

    def test_requests_ca_bundle_takes_precedence_over_cached(self, tmp_path):
        """REQUESTS_CA_BUNDLE env var takes priority over auto-fetched cert."""
        env_ca = str(tmp_path / "env_ca.pem")
        (tmp_path / "env_ca.pem").write_text("cert", encoding="utf-8")
        cached_pem = str(tmp_path / "cached.pem")

        with patch.dict("os.environ", {"REQUESTS_CA_BUNDLE": env_ca}, clear=True):
            with patch.object(cert_utils, "ensure_ca_bundle", return_value=cached_pem) as mock_ensure:
                result = cert_utils.get_ssl_verify("example.com")

        assert result == env_ca
        mock_ensure.assert_not_called()

    @pytest.mark.parametrize("hostname", ["api.github.com", "github.com", "registry.npmjs.org"])
    def test_passes_hostname_to_ensure_ca_bundle(self, hostname):
        """Passes the correct hostname to ensure_ca_bundle."""
        with patch.dict("os.environ", {}, clear=True):
            with patch.object(cert_utils, "ensure_ca_bundle", return_value=None) as mock_ensure:
                cert_utils.get_ssl_verify(hostname)

        mock_ensure.assert_called_once_with(hostname)
