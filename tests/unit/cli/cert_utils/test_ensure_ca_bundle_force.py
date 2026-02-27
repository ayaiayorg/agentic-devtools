"""Tests for ensure_ca_bundle with force=True parameter."""

from unittest.mock import patch

from agentic_devtools.cli import cert_utils


class TestEnsureCaBundleForce:
    """Tests for ensure_ca_bundle force parameter."""

    def test_force_deletes_cached_file_and_refetches(self, tmp_path):
        """When force=True, deletes existing cache and re-fetches."""
        stale_pem = "-----BEGIN CERTIFICATE-----\nstale\n-----END CERTIFICATE-----"
        fresh_chain = (
            "-----BEGIN CERTIFICATE-----\nserver\n-----END CERTIFICATE-----\n"
            "-----BEGIN CERTIFICATE-----\nca\n-----END CERTIFICATE-----"
        )
        cache_file = tmp_path / "example.com.pem"
        cache_file.write_text(stale_pem, encoding="utf-8")

        with patch.object(cert_utils, "fetch_certificate_chain_openssl", return_value=fresh_chain):
            result = cert_utils.ensure_ca_bundle("example.com", cache_file=cache_file, force=True)

        assert result == str(cache_file.resolve())
        content = cache_file.read_text(encoding="utf-8")
        assert "stale" not in content
        assert "server" in content

    def test_force_false_returns_cached_without_refetch(self, tmp_path):
        """When force=False (default), returns cached file without re-fetching."""
        existing = "-----BEGIN CERTIFICATE-----\ncached\n-----END CERTIFICATE-----"
        cache_file = tmp_path / "example.com.pem"
        cache_file.write_text(existing, encoding="utf-8")

        with patch.object(cert_utils, "fetch_certificate_chain_openssl") as mock_openssl:
            result = cert_utils.ensure_ca_bundle("example.com", cache_file=cache_file)

        mock_openssl.assert_not_called()
        assert result == str(cache_file.resolve())

    def test_force_on_missing_file_still_fetches(self, tmp_path):
        """When force=True but no cached file exists, still fetches normally."""
        fresh_chain = (
            "-----BEGIN CERTIFICATE-----\nserver\n-----END CERTIFICATE-----\n"
            "-----BEGIN CERTIFICATE-----\nca\n-----END CERTIFICATE-----"
        )
        cache_file = tmp_path / "example.com.pem"
        assert not cache_file.exists()

        with patch.object(cert_utils, "fetch_certificate_chain_openssl", return_value=fresh_chain):
            result = cert_utils.ensure_ca_bundle("example.com", cache_file=cache_file, force=True)

        assert result == str(cache_file.resolve())

    def test_force_continues_when_unlink_fails(self, tmp_path):
        """When force=True and unlink raises OSError, returns existing cache."""
        stale_pem = "-----BEGIN CERTIFICATE-----\nstale\n-----END CERTIFICATE-----"
        fresh_chain = (
            "-----BEGIN CERTIFICATE-----\nserver\n-----END CERTIFICATE-----\n"
            "-----BEGIN CERTIFICATE-----\nca\n-----END CERTIFICATE-----"
        )
        cache_file = tmp_path / "example.com.pem"
        cache_file.write_text(stale_pem, encoding="utf-8")

        with patch.object(type(cache_file), "unlink", side_effect=OSError("permission denied")):
            with patch.object(cert_utils, "fetch_certificate_chain_openssl", return_value=fresh_chain):
                # Should not raise — the OSError from unlink is caught.
                # The cache file still contains the old cert, so it's returned from cache.
                result = cert_utils.ensure_ca_bundle("example.com", cache_file=cache_file, force=True)

        assert result == str(cache_file.resolve())
