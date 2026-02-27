"""Tests for ssl_request_with_retry."""

from unittest.mock import MagicMock, call, patch

import pytest
import requests

from agentic_devtools.cli import cert_utils


class TestSslRequestWithRetry:
    """Tests for ssl_request_with_retry."""

    def test_returns_response_on_success(self):
        """Returns the response object when the first attempt succeeds."""
        mock_response = MagicMock()
        with patch.dict("os.environ", {}, clear=True):
            with patch.object(cert_utils, "get_ssl_verify", return_value=True):
                with patch("requests.get", return_value=mock_response) as mock_get:
                    result = cert_utils.ssl_request_with_retry("https://example.com", "example.com")
        assert result is mock_response
        mock_get.assert_called_once_with("https://example.com", timeout=30, stream=False, verify=True)

    def test_passes_timeout_and_stream(self):
        """Forwards timeout and stream parameters to requests.get."""
        mock_response = MagicMock()
        with patch.dict("os.environ", {}, clear=True):
            with patch.object(cert_utils, "get_ssl_verify", return_value=True):
                with patch("requests.get", return_value=mock_response) as mock_get:
                    cert_utils.ssl_request_with_retry("https://example.com", "example.com", timeout=120, stream=True)
        mock_get.assert_called_once_with("https://example.com", timeout=120, stream=True, verify=True)

    def test_retries_with_fresh_ca_bundle_on_ssl_error(self, tmp_path):
        """On SSLError, force-refetches CA bundle and retries the request."""
        cached_pem = str(tmp_path / "example.com.pem")
        fresh_pem = str(tmp_path / "example.com-fresh.pem")
        mock_response = MagicMock()
        ssl_error = requests.exceptions.SSLError("cert verify failed")

        with patch.dict("os.environ", {}, clear=True):
            with patch.object(cert_utils, "get_ssl_verify", return_value=cached_pem):
                with patch.object(cert_utils, "ensure_ca_bundle", return_value=fresh_pem) as mock_ensure:
                    with patch("requests.get", side_effect=[ssl_error, mock_response]) as mock_get:
                        result = cert_utils.ssl_request_with_retry("https://example.com", "example.com")

        assert result is mock_response
        mock_ensure.assert_called_once_with("example.com", force=True)
        assert mock_get.call_count == 2
        assert mock_get.call_args_list[1] == call("https://example.com", timeout=30, stream=False, verify=fresh_pem)

    def test_raises_and_prints_help_when_retry_also_fails(self, capsys):
        """Raises SSLError and prints help when both attempts fail."""
        ssl_error = requests.exceptions.SSLError("cert verify failed")
        fresh_pem = "/tmp/fresh.pem"

        with patch.dict("os.environ", {}, clear=True):
            with patch.object(cert_utils, "get_ssl_verify", return_value=True):
                with patch.object(cert_utils, "ensure_ca_bundle", return_value=fresh_pem):
                    with patch("requests.get", side_effect=ssl_error):
                        with pytest.raises(requests.exceptions.SSLError):
                            cert_utils.ssl_request_with_retry("https://example.com", "example.com")

        err = capsys.readouterr().err
        assert "agdt-setup-certs" in err

    def test_reraises_retry_error_not_original(self, capsys):
        """Re-raises the retry SSLError, not the original, for accurate tracebacks."""
        original_error = requests.exceptions.SSLError("original cert error")
        retry_error = requests.exceptions.SSLError("retry cert error")
        fresh_pem = "/tmp/fresh.pem"

        with patch.dict("os.environ", {}, clear=True):
            with patch.object(cert_utils, "get_ssl_verify", return_value=True):
                with patch.object(cert_utils, "ensure_ca_bundle", return_value=fresh_pem):
                    with patch("requests.get", side_effect=[original_error, retry_error]):
                        with pytest.raises(requests.exceptions.SSLError, match="retry cert error"):
                            cert_utils.ssl_request_with_retry("https://example.com", "example.com")

    def test_skips_retry_when_no_fresh_bundle(self, capsys):
        """Raises SSLError immediately when ensure_ca_bundle returns None."""
        ssl_error = requests.exceptions.SSLError("cert verify failed")

        with patch.dict("os.environ", {}, clear=True):
            with patch.object(cert_utils, "get_ssl_verify", return_value=True):
                with patch.object(cert_utils, "ensure_ca_bundle", return_value=None):
                    with patch("requests.get", side_effect=ssl_error) as mock_get:
                        with pytest.raises(requests.exceptions.SSLError):
                            cert_utils.ssl_request_with_retry("https://example.com", "example.com")

        # requests.get called only once (no retry with no fresh bundle)
        assert mock_get.call_count == 1
        err = capsys.readouterr().err
        assert "agdt-setup-certs" in err

    def test_no_verify_ssl_env_var_disables_verification(self, capsys):
        """Uses verify=False and prints warning when AGDT_NO_VERIFY_SSL is set."""
        mock_response = MagicMock()

        with patch.dict("os.environ", {"AGDT_NO_VERIFY_SSL": "1"}):
            with patch("requests.get", return_value=mock_response) as mock_get:
                result = cert_utils.ssl_request_with_retry("https://example.com", "example.com")

        assert result is mock_response
        mock_get.assert_called_once_with("https://example.com", timeout=30, stream=False, verify=False)
        err = capsys.readouterr().err
        assert "SSL verification disabled" in err

    def test_no_verify_ssl_does_not_retry(self, capsys):
        """Does not attempt retry logic when AGDT_NO_VERIFY_SSL is set."""
        mock_response = MagicMock()

        with patch.dict("os.environ", {"AGDT_NO_VERIFY_SSL": "1"}):
            with patch.object(cert_utils, "ensure_ca_bundle") as mock_ensure:
                with patch("requests.get", return_value=mock_response):
                    cert_utils.ssl_request_with_retry("https://example.com", "example.com")

        mock_ensure.assert_not_called()

    def test_retries_even_when_fresh_bundle_same_path_as_original(self, tmp_path, capsys):
        """Retries with force-refreshed bundle even when the cache path is unchanged."""
        pem = str(tmp_path / "example.com.pem")
        ssl_error = requests.exceptions.SSLError("cert verify failed")
        mock_response = MagicMock()

        with patch.dict("os.environ", {}, clear=True):
            with patch.object(cert_utils, "get_ssl_verify", return_value=pem):
                with patch.object(cert_utils, "ensure_ca_bundle", return_value=pem):
                    with patch("requests.get", side_effect=[ssl_error, mock_response]) as mock_get:
                        result = cert_utils.ssl_request_with_retry("https://example.com", "example.com")

        # Retry should happen because the file contents may have changed
        assert result is mock_response
        assert mock_get.call_count == 2
