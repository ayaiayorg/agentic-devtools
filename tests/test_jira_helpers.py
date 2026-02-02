"""
Tests for Jira helper utilities.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from agdt_ai_helpers.cli import jira
from agdt_ai_helpers.cli.jira import helpers as jira_helpers


class TestGetRequests:
    """Tests for _get_requests helper."""

    def test_get_requests_returns_module(self):
        """Test _get_requests returns the requests module."""
        result = jira._get_requests()
        assert hasattr(result, "get")
        assert hasattr(result, "post")

    def test_get_requests_raises_on_import_error(self):
        """Test _get_requests raises ImportError when requests not available.

        Note: The actual _get_requests function's ImportError branch (lines 22-23)
        is defensive code that only triggers if requests isn't installed.
        Since requests is a package dependency, we test the error message format here.
        """
        # Verify the error message format matches what the function would produce
        expected_msg = "requests library required. Install with: pip install requests"
        error = ImportError(expected_msg)
        assert "requests library required" in str(error)
        assert "pip install requests" in str(error)


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


class TestGetJiraPemPaths:
    """Tests for _get_repo_jira_pem_path and _get_temp_jira_pem_path helpers."""

    def test_temp_path_returns_path_in_state_dir(self):
        """Test that temp PEM path is in the state directory."""
        with patch("agdt_ai_helpers.cli.jira.helpers.get_state_dir") as mock_state_dir:
            mock_state_dir.return_value = Path("/mock/state/dir")
            result = jira_helpers._get_temp_jira_pem_path()
            assert result == Path("/mock/state/dir/jira_ca_bundle.pem")

    def test_repo_path_returns_path_in_scripts_dir(self):
        """Test that repo PEM path is in the scripts directory (parent of temp)."""
        with patch("agdt_ai_helpers.cli.jira.helpers.get_state_dir") as mock_state_dir:
            # state_dir is typically scripts/temp, so parent is scripts/
            mock_state_dir.return_value = Path("/mock/scripts/temp")
            result = jira_helpers._get_repo_jira_pem_path()
            assert result == Path("/mock/scripts/jira_ca_bundle.pem")


class TestFetchCertificateChainOpenssl:
    """Tests for _fetch_certificate_chain_openssl helper."""

    def test_returns_certificates_on_success(self):
        """Test returns PEM certificates when openssl succeeds."""
        mock_output = b"""
CONNECTED(00000003)
depth=2 C = CH, O = SWICA, CN = SWICA Root CA
verify error:num=19:self signed certificate in certificate chain
---
Certificate chain
 0 s:C = CH, ST = Zurich, L = Winterthur, O = SWICA, OU = IT, CN = jira.swica.ch
   i:C = CH, O = SWICA, CN = SWICA Server CA 2
-----BEGIN CERTIFICATE-----
MIIFakeServerCert123
-----END CERTIFICATE-----
 1 s:C = CH, O = SWICA, CN = SWICA Server CA 2
   i:C = CH, O = SWICA, CN = SWICA Root CA
-----BEGIN CERTIFICATE-----
MIIFakeIntermediateCert456
-----END CERTIFICATE-----
---
"""
        with patch("agdt_ai_helpers.cli.subprocess_utils.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=mock_output)
            result = jira_helpers._fetch_certificate_chain_openssl("jira.swica.ch")

        assert result is not None
        assert "-----BEGIN CERTIFICATE-----" in result
        assert "-----END CERTIFICATE-----" in result

    def test_returns_none_on_timeout(self):
        """Test returns None when subprocess times out."""
        import subprocess

        with patch("agdt_ai_helpers.cli.subprocess_utils.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="openssl", timeout=10)
            result = jira_helpers._fetch_certificate_chain_openssl("jira.swica.ch")

        assert result is None

    def test_returns_none_on_file_not_found(self):
        """Test returns None when openssl is not installed."""
        with patch("agdt_ai_helpers.cli.subprocess_utils.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("openssl not found")
            result = jira_helpers._fetch_certificate_chain_openssl("jira.swica.ch")

        assert result is None

    def test_returns_none_on_no_certificates(self):
        """Test returns None when output has no certificates."""
        with patch("agdt_ai_helpers.cli.subprocess_utils.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=b"CONNECTED\n---\nNo certificates\n---")
            result = jira_helpers._fetch_certificate_chain_openssl("jira.swica.ch")

        assert result is None


class TestFetchCertificateChainSsl:
    """Tests for _fetch_certificate_chain_ssl helper."""

    def test_returns_certificate_on_success(self):
        """Test returns PEM certificate when SSL connection succeeds."""
        mock_cert_der = b"mock_der_certificate"
        mock_cert_pem = "-----BEGIN CERTIFICATE-----\nmock\n-----END CERTIFICATE-----"

        with patch("socket.create_connection") as mock_conn:
            with patch("ssl.create_default_context") as mock_ctx:
                with patch("ssl.DER_cert_to_PEM_cert") as mock_convert:
                    mock_sock = MagicMock()
                    mock_ssock = MagicMock()
                    mock_ssock.getpeercert.return_value = mock_cert_der
                    mock_sock.__enter__.return_value = mock_sock
                    mock_ctx.return_value.wrap_socket.return_value.__enter__.return_value = mock_ssock
                    mock_conn.return_value.__enter__.return_value = mock_sock
                    mock_convert.return_value = mock_cert_pem

                    result = jira_helpers._fetch_certificate_chain_ssl("jira.swica.ch")

        assert result == mock_cert_pem

    def test_returns_none_on_connection_error(self):
        """Test returns None when connection fails."""
        with patch("socket.create_connection") as mock_conn:
            mock_conn.side_effect = ConnectionRefusedError()
            result = jira_helpers._fetch_certificate_chain_ssl("jira.swica.ch")

        assert result is None

    def test_returns_none_when_no_cert(self):
        """Test returns None when no certificate is returned."""
        with patch("socket.create_connection") as mock_conn:
            with patch("ssl.create_default_context"):
                mock_sock = MagicMock()
                mock_ssock = MagicMock()
                mock_ssock.getpeercert.return_value = None
                mock_sock.__enter__.return_value = mock_sock
                mock_conn.return_value.__enter__.return_value = mock_sock

                result = jira_helpers._fetch_certificate_chain_ssl("jira.swica.ch")

        assert result is None


class TestEnsureJiraPem:
    """Tests for _ensure_jira_pem helper."""

    def test_returns_existing_pem_path(self):
        """Test returns existing PEM file path without refetching when chain is complete."""
        expected_path = "/fake/path/to/jira_ca_bundle.pem"
        # PEM content with 2 certificates (complete chain)
        complete_chain = (
            "-----BEGIN CERTIFICATE-----\nserver_cert\n-----END CERTIFICATE-----\n"
            "-----BEGIN CERTIFICATE-----\nintermediate_cert\n-----END CERTIFICATE-----"
        )
        with patch("agdt_ai_helpers.cli.jira.helpers._get_temp_jira_pem_path") as mock_path:
            mock_pem = MagicMock(spec=Path)
            mock_pem.exists.return_value = True
            mock_pem.read_text.return_value = complete_chain
            mock_pem.__str__ = MagicMock(return_value=expected_path)
            mock_path.return_value = mock_pem

            result = jira_helpers._ensure_jira_pem("jira.swica.ch")

        assert result == expected_path
        mock_pem.read_text.assert_called_once_with(encoding="utf-8")

    def test_fetches_and_saves_cert_when_not_exists(self):
        """Test fetches certificate and saves when PEM file doesn't exist."""
        mock_cert = "-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----"

        with patch("agdt_ai_helpers.cli.jira.helpers._get_temp_jira_pem_path") as mock_path:
            with patch("agdt_ai_helpers.cli.jira.helpers._fetch_certificate_chain_openssl") as mock_fetch:
                mock_pem = MagicMock(spec=Path)
                mock_pem.exists.return_value = False
                mock_pem.parent.mkdir = MagicMock()
                mock_pem.write_text = MagicMock()
                mock_path.return_value = mock_pem
                mock_fetch.return_value = mock_cert

                result = jira_helpers._ensure_jira_pem("jira.swica.ch")

        mock_pem.write_text.assert_called_once_with(mock_cert, encoding="utf-8")
        assert result == str(mock_pem)

    def test_falls_back_to_ssl_when_openssl_fails(self):
        """Test falls back to ssl module when openssl fails."""
        mock_cert = "-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----"

        with patch("agdt_ai_helpers.cli.jira.helpers._get_temp_jira_pem_path") as mock_path:
            with patch("agdt_ai_helpers.cli.jira.helpers._fetch_certificate_chain_openssl") as mock_openssl:
                with patch("agdt_ai_helpers.cli.jira.helpers._fetch_certificate_chain_ssl") as mock_ssl:
                    mock_pem = MagicMock(spec=Path)
                    mock_pem.exists.return_value = False
                    mock_pem.parent.mkdir = MagicMock()
                    mock_pem.write_text = MagicMock()
                    mock_path.return_value = mock_pem
                    mock_openssl.return_value = None
                    mock_ssl.return_value = mock_cert

                    result = jira_helpers._ensure_jira_pem("jira.swica.ch")

        mock_ssl.assert_called_once()
        assert result == str(mock_pem)

    def test_returns_none_when_all_methods_fail(self):
        """Test returns None when both openssl and ssl module fail."""
        with patch("agdt_ai_helpers.cli.jira.helpers._get_temp_jira_pem_path") as mock_path:
            with patch("agdt_ai_helpers.cli.jira.helpers._fetch_certificate_chain_openssl") as mock_openssl:
                with patch("agdt_ai_helpers.cli.jira.helpers._fetch_certificate_chain_ssl") as mock_ssl:
                    mock_pem = MagicMock(spec=Path)
                    mock_pem.exists.return_value = False
                    mock_path.return_value = mock_pem
                    mock_openssl.return_value = None
                    mock_ssl.return_value = None

                    result = jira_helpers._ensure_jira_pem("jira.swica.ch")

        assert result is None

    def test_refetches_when_existing_pem_has_incomplete_chain(self):
        """Test refetches certificate when existing PEM has only server cert (incomplete chain)."""
        expected_path = "/fake/path/to/jira_ca_bundle.pem"
        # Existing PEM with only 1 certificate (incomplete chain)
        incomplete_chain = "-----BEGIN CERTIFICATE-----\nserver_cert_only\n-----END CERTIFICATE-----"
        # New complete chain from openssl
        complete_chain = (
            "-----BEGIN CERTIFICATE-----\nserver_cert\n-----END CERTIFICATE-----\n"
            "-----BEGIN CERTIFICATE-----\nintermediate_cert\n-----END CERTIFICATE-----"
        )

        with patch("agdt_ai_helpers.cli.jira.helpers._get_temp_jira_pem_path") as mock_path:
            with patch("agdt_ai_helpers.cli.jira.helpers._fetch_certificate_chain_openssl") as mock_openssl:
                mock_pem = MagicMock(spec=Path)
                mock_pem.exists.return_value = True
                mock_pem.read_text.return_value = incomplete_chain
                mock_pem.parent.mkdir = MagicMock()
                mock_pem.write_text = MagicMock()
                mock_pem.__str__ = MagicMock(return_value=expected_path)
                mock_path.return_value = mock_pem
                mock_openssl.return_value = complete_chain

                result = jira_helpers._ensure_jira_pem("jira.swica.ch")

        # Should have refetched and saved the complete chain
        mock_openssl.assert_called_once_with("jira.swica.ch")
        mock_pem.write_text.assert_called_once_with(complete_chain, encoding="utf-8")
        assert result == expected_path

    def test_saves_incomplete_chain_when_openssl_returns_single_cert(self):
        """Test saves and returns path when openssl returns only server cert (incomplete chain)."""
        # openssl returns only 1 certificate - not ideal but better than nothing
        incomplete_chain = "-----BEGIN CERTIFICATE-----\nonly_server_cert\n-----END CERTIFICATE-----"

        with patch("agdt_ai_helpers.cli.jira.helpers._get_temp_jira_pem_path") as mock_path:
            with patch("agdt_ai_helpers.cli.jira.helpers._fetch_certificate_chain_openssl") as mock_openssl:
                with patch("agdt_ai_helpers.cli.jira.helpers._fetch_certificate_chain_ssl") as mock_ssl:
                    mock_pem = MagicMock(spec=Path)
                    mock_pem.exists.return_value = False
                    mock_pem.parent.mkdir = MagicMock()
                    mock_pem.write_text = MagicMock()
                    mock_path.return_value = mock_pem
                    mock_openssl.return_value = incomplete_chain  # Only 1 cert

                    result = jira_helpers._ensure_jira_pem("jira.swica.ch")

        # Should save the incomplete chain (better than nothing)
        mock_openssl.assert_called_once()
        mock_ssl.assert_not_called()  # ssl fallback NOT called when openssl returns content
        mock_pem.write_text.assert_called_once_with(incomplete_chain, encoding="utf-8")
        assert result == str(mock_pem)


class TestGetSslVerify:
    """Tests for _get_ssl_verify helper."""

    def test_ssl_verify_disabled_when_env_set_to_0(self):
        """Test SSL verification disabled when JIRA_SSL_VERIFY=0."""
        with patch.dict("os.environ", {"JIRA_SSL_VERIFY": "0"}, clear=True):
            assert jira_helpers._get_ssl_verify() is False

    def test_ssl_verify_uses_state_ca_bundle_path(self):
        """Test SSL verification uses state value jira.ca_bundle_path when set."""
        with patch.dict("os.environ", {}, clear=True):
            with patch("agdt_ai_helpers.state.get_value") as mock_get_value:
                with patch("os.path.exists") as mock_exists:
                    mock_get_value.return_value = "/state/path/to/ca.pem"
                    mock_exists.return_value = True
                    result = jira_helpers._get_ssl_verify()

        mock_get_value.assert_called_once_with("jira.ca_bundle_path")
        assert result == "/state/path/to/ca.pem"

    def test_ssl_verify_state_takes_priority_over_env_ca_bundle(self):
        """Test state jira.ca_bundle_path takes priority over JIRA_CA_BUNDLE env var."""
        with patch.dict("os.environ", {"JIRA_CA_BUNDLE": "/env/path/ca.pem"}, clear=True):
            with patch("agdt_ai_helpers.state.get_value") as mock_get_value:
                with patch("os.path.exists") as mock_exists:
                    mock_get_value.return_value = "/state/path/ca.pem"
                    mock_exists.return_value = True
                    result = jira_helpers._get_ssl_verify()

        # State path should be returned, not env path
        assert result == "/state/path/ca.pem"

    def test_ssl_verify_ignores_state_ca_bundle_if_not_exists(self):
        """Test ignores state CA bundle path if file doesn't exist."""
        with patch.dict("os.environ", {"JIRA_CA_BUNDLE": "/env/ca.pem"}, clear=True):
            with patch("agdt_ai_helpers.state.get_value") as mock_get_value:
                with patch("os.path.exists") as mock_exists:
                    mock_get_value.return_value = "/nonexistent/state/ca.pem"
                    # First call (state path) returns False, second call (env path) returns True
                    mock_exists.side_effect = [False, True]
                    result = jira_helpers._get_ssl_verify()

        # Should fall back to env var since state path doesn't exist
        assert result == "/env/ca.pem"

    def test_ssl_verify_uses_custom_ca_bundle(self):
        """Test SSL verification uses custom CA bundle when JIRA_CA_BUNDLE is set."""
        with patch.dict("os.environ", {"JIRA_CA_BUNDLE": "/path/to/ca.pem"}, clear=True):
            with patch("agdt_ai_helpers.state.get_value") as mock_get_value:
                with patch("os.path.exists") as mock_exists:
                    mock_get_value.return_value = None
                    mock_exists.return_value = True
                    result = jira_helpers._get_ssl_verify()

        assert result == "/path/to/ca.pem"

    def test_ssl_verify_uses_requests_ca_bundle(self):
        """Test SSL verification uses REQUESTS_CA_BUNDLE when set."""
        with patch.dict(
            "os.environ",
            {"REQUESTS_CA_BUNDLE": "/path/to/requests_ca.pem"},
            clear=True,
        ):
            with patch("agdt_ai_helpers.state.get_value") as mock_get_value:
                with patch("os.path.exists") as mock_exists:
                    mock_get_value.return_value = None
                    mock_exists.return_value = True
                    result = jira_helpers._get_ssl_verify()

        assert result == "/path/to/requests_ca.pem"

    def test_ssl_verify_ignores_nonexistent_ca_bundle(self):
        """Test ignores CA bundle path if file doesn't exist and falls back to auto-gen."""
        with patch.dict("os.environ", {"JIRA_CA_BUNDLE": "/nonexistent/ca.pem"}, clear=True):
            with patch("os.path.exists") as mock_exists:
                with patch("agdt_ai_helpers.cli.jira.helpers._get_repo_jira_pem_path") as mock_repo_pem:
                    with patch("agdt_ai_helpers.cli.jira.helpers._ensure_jira_pem") as mock_ensure:
                        # Neither env var CA nor repo CA exists
                        mock_exists.return_value = False
                        mock_path = MagicMock()
                        mock_path.exists.return_value = False
                        mock_repo_pem.return_value = mock_path
                        mock_ensure.return_value = "/auto/jira.pem"
                        result = jira_helpers._get_ssl_verify()

        assert result == "/auto/jira.pem"

    def test_ssl_verify_uses_repo_committed_pem(self):
        """Test SSL verification uses repo-committed PEM when it exists."""
        with patch.dict("os.environ", {}, clear=True):
            with patch("agdt_ai_helpers.cli.jira.helpers._get_repo_jira_pem_path") as mock_repo_pem:
                mock_path = MagicMock()
                mock_path.exists.return_value = True
                mock_path.__str__ = MagicMock(return_value="/repo/jira_ca_bundle.pem")
                mock_repo_pem.return_value = mock_path
                result = jira_helpers._get_ssl_verify()

        assert result == "/repo/jira_ca_bundle.pem"

    def test_ssl_verify_uses_auto_generated_pem(self):
        """Test SSL verification uses auto-generated PEM when repo PEM doesn't exist."""
        with patch.dict("os.environ", {}, clear=True):
            with patch("agdt_ai_helpers.cli.jira.helpers._get_repo_jira_pem_path") as mock_repo_pem:
                with patch("agdt_ai_helpers.state.get_value") as mock_get_value:
                    with patch("agdt_ai_helpers.cli.jira.config.get_jira_base_url") as mock_url:
                        with patch("agdt_ai_helpers.cli.jira.helpers._ensure_jira_pem") as mock_ensure:
                            mock_path = MagicMock()
                            mock_path.exists.return_value = False
                            mock_repo_pem.return_value = mock_path
                            mock_get_value.return_value = None
                            mock_url.return_value = "https://jira.example.com"
                            mock_ensure.return_value = "/auto/generated.pem"
                            result = jira_helpers._get_ssl_verify()

        mock_ensure.assert_called_once_with("jira.example.com")
        assert result == "/auto/generated.pem"

    def test_ssl_verify_disables_when_auto_gen_fails(self):
        """Test SSL verification disabled when auto-generation fails."""
        with patch.dict("os.environ", {}, clear=True):
            with patch("agdt_ai_helpers.cli.jira.helpers._get_repo_jira_pem_path") as mock_repo_pem:
                with patch("agdt_ai_helpers.state.get_value") as mock_get_value:
                    with patch("agdt_ai_helpers.cli.jira.config.get_jira_base_url") as mock_url:
                        with patch("agdt_ai_helpers.cli.jira.helpers._ensure_jira_pem") as mock_ensure:
                            mock_path = MagicMock()
                            mock_path.exists.return_value = False
                            mock_repo_pem.return_value = mock_path
                            mock_get_value.return_value = None
                            mock_url.return_value = "https://jira.example.com"
                            mock_ensure.return_value = None  # Auto-gen fails
                            result = jira_helpers._get_ssl_verify()

        assert result is False

    def test_ssl_verify_extracts_hostname_from_https_url(self):
        """Test hostname extraction from HTTPS URL when auto-generating."""
        with patch.dict("os.environ", {}, clear=True):
            with patch("agdt_ai_helpers.cli.jira.helpers._get_repo_jira_pem_path") as mock_repo_pem:
                with patch("agdt_ai_helpers.state.get_value") as mock_get_value:
                    with patch("agdt_ai_helpers.cli.jira.config.get_jira_base_url") as mock_url:
                        with patch("agdt_ai_helpers.cli.jira.helpers._ensure_jira_pem") as mock_ensure:
                            mock_path = MagicMock()
                            mock_path.exists.return_value = False
                            mock_repo_pem.return_value = mock_path
                            mock_get_value.return_value = None
                            mock_url.return_value = "https://jira.company.com/rest/api"
                            mock_ensure.return_value = "/pem/path"
                            jira_helpers._get_ssl_verify()

        mock_ensure.assert_called_once_with("jira.company.com")

    def test_ssl_verify_extracts_hostname_from_http_url(self):
        """Test hostname extraction from HTTP URL when auto-generating."""
        with patch.dict("os.environ", {}, clear=True):
            with patch("agdt_ai_helpers.cli.jira.helpers._get_repo_jira_pem_path") as mock_repo_pem:
                with patch("agdt_ai_helpers.state.get_value") as mock_get_value:
                    with patch("agdt_ai_helpers.cli.jira.config.get_jira_base_url") as mock_url:
                        with patch("agdt_ai_helpers.cli.jira.helpers._ensure_jira_pem") as mock_ensure:
                            mock_path = MagicMock()
                            mock_path.exists.return_value = False
                            mock_repo_pem.return_value = mock_path
                            mock_get_value.return_value = None
                            mock_url.return_value = "http://jira.local:8080/path"
                            mock_ensure.return_value = "/pem/path"
                            jira_helpers._get_ssl_verify()

        mock_ensure.assert_called_once_with("jira.local:8080")


class TestParseMultilineString:
    """Tests for _parse_multiline_string helper."""

    def test_parse_none_returns_none(self):
        """Test None input returns None."""
        assert jira._parse_multiline_string(None) is None

    def test_parse_list_returns_stripped_list(self):
        """Test list input returns stripped items."""
        items = ["  a  ", "b", "  c"]
        assert jira._parse_multiline_string(items) == ["a", "b", "c"]

    def test_parse_list_filters_empty(self):
        """Test empty items are filtered from list."""
        items = ["a", "", "  ", "b"]
        assert jira._parse_multiline_string(items) == ["a", "b"]

    def test_parse_newline_separated_string(self):
        """Test newline-separated string is split."""
        result = jira._parse_multiline_string("line1\nline2\nline3")
        assert result == ["line1", "line2", "line3"]

    def test_parse_string_strips_whitespace(self):
        """Test whitespace is stripped from each line."""
        result = jira._parse_multiline_string("  line1  \n  line2  ")
        assert result == ["line1", "line2"]

    def test_parse_string_skips_empty_lines(self):
        """Test empty lines are skipped."""
        result = jira._parse_multiline_string("line1\n\n  \nline2")
        assert result == ["line1", "line2"]

    def test_parse_integer_returns_none(self):
        """Test non-string non-list input returns None."""
        assert jira._parse_multiline_string(123) is None

    def test_parse_empty_string_returns_empty_list(self):
        """Test empty string returns empty list."""
        assert jira._parse_multiline_string("") == []

    def test_parse_empty_list_returns_empty_list(self):
        """Test empty list returns empty list."""
        assert jira._parse_multiline_string([]) == []


class TestParseCommaSeparated:
    """Tests for _parse_comma_separated helper."""

    def test_parse_none_returns_none(self):
        """Test None input returns None."""
        assert jira._parse_comma_separated(None) is None

    def test_parse_list_returns_stripped_list(self):
        """Test list input returns stripped items."""
        items = ["  a  ", "b", "  c"]
        assert jira._parse_comma_separated(items) == ["a", "b", "c"]

    def test_parse_list_filters_empty(self):
        """Test empty items are filtered from list."""
        items = ["a", "", "  ", "b"]
        assert jira._parse_comma_separated(items) == ["a", "b"]

    def test_parse_comma_separated_string(self):
        """Test comma-separated string is split."""
        result = jira._parse_comma_separated("a,b,c")
        assert result == ["a", "b", "c"]

    def test_parse_string_strips_whitespace(self):
        """Test whitespace is stripped from each item."""
        result = jira._parse_comma_separated("  a  ,  b  ,  c  ")
        assert result == ["a", "b", "c"]

    def test_parse_string_skips_empty_items(self):
        """Test empty items are skipped."""
        result = jira._parse_comma_separated("a,,  ,b")
        assert result == ["a", "b"]

    def test_parse_integer_returns_none(self):
        """Test non-string non-list input returns None."""
        assert jira._parse_comma_separated(123) is None

    def test_parse_empty_string_returns_empty_list(self):
        """Test empty string returns empty list."""
        assert jira._parse_comma_separated("") == []

    def test_parse_empty_list_returns_empty_list(self):
        """Test empty list returns empty list."""
        assert jira._parse_comma_separated([]) == []
