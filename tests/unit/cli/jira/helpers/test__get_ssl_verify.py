"""
Tests for Jira helper utilities.
"""

from unittest.mock import MagicMock, patch

from agdt_ai_helpers.cli.jira import helpers as jira_helpers


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

