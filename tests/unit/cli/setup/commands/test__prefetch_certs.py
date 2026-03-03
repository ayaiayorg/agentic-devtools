"""Tests for _prefetch_certs."""

from unittest.mock import patch

import pytest

from agentic_devtools.cli.setup import commands


@pytest.fixture(autouse=True)
def mock_setup_network():
    """Override the conftest autouse mock to test _prefetch_certs directly."""
    yield


class TestPrefetchCerts:
    """Tests for _prefetch_certs."""

    def test_prints_cached_message_when_bundles_exist(self, capsys, tmp_path):
        """Prints cached messages when ensure_ca_bundle returns paths."""
        pem_path = str(tmp_path / "cert.pem")

        with patch.object(commands, "_ensure_ca_bundle", return_value=pem_path):
            with patch.object(commands, "_build_unified_ca_bundle", return_value=None):
                with patch.object(commands, "Path") as mock_path_cls:
                    mock_npmrc = mock_path_cls.home.return_value.__truediv__.return_value.__truediv__.return_value
                    mock_npmrc.parent = tmp_path
                    commands._prefetch_certs()

        out = capsys.readouterr().out
        assert "CA bundle cached for api.github.com" in out
        assert "CA bundle cached for github.com" in out
        assert "CA bundle cached for dev.azure.com" in out
        assert "CA bundle cached for release-assets.githubusercontent.com" in out
        assert "CA bundle cached for registry.npmjs.org" in out

    def test_includes_jira_hostname(self, capsys, tmp_path):
        """Fetches cert for the Jira hostname resolved from get_jira_base_url."""
        pem_path = str(tmp_path / "cert.pem")

        with patch.object(commands, "_ensure_ca_bundle", return_value=pem_path) as mock_ensure:
            with patch.object(commands, "_build_unified_ca_bundle", return_value=None):
                with patch("agentic_devtools.cli.setup.commands.Path") as mock_path_cls:
                    mock_npmrc = mock_path_cls.home.return_value.__truediv__.return_value.__truediv__.return_value
                    mock_npmrc.parent = tmp_path
                    # Patch at definition point; all imports see the mock
                    with patch(
                        "agentic_devtools.cli.jira.config.get_jira_base_url", return_value="https://jira.example.com"
                    ):
                        commands._prefetch_certs()

        called_hostnames = [c.args[0] for c in mock_ensure.call_args_list]
        assert "jira.example.com" in called_hostnames

    def test_strips_port_from_jira_hostname(self, capsys, tmp_path):
        """Strips port from Jira URL so ensure_ca_bundle receives a clean hostname."""
        pem_path = str(tmp_path / "cert.pem")

        with patch.object(commands, "_ensure_ca_bundle", return_value=pem_path) as mock_ensure:
            with patch.object(commands, "_build_unified_ca_bundle", return_value=None):
                with patch("agentic_devtools.cli.setup.commands.Path") as mock_path_cls:
                    mock_npmrc = mock_path_cls.home.return_value.__truediv__.return_value.__truediv__.return_value
                    mock_npmrc.parent = tmp_path
                    with patch(
                        "agentic_devtools.cli.jira.config.get_jira_base_url",
                        return_value="https://jira.example.com:8443",
                    ):
                        commands._prefetch_certs()

        called_hostnames = [c.args[0] for c in mock_ensure.call_args_list]
        # Must be the bare hostname without port
        assert "jira.example.com" in called_hostnames
        assert "jira.example.com:8443" not in called_hostnames

    def test_prints_warning_message_when_bundles_missing(self, capsys):
        """Prints warning messages when ensure_ca_bundle returns None."""
        with patch.object(commands, "_ensure_ca_bundle", return_value=None):
            with patch.object(commands, "_build_unified_ca_bundle", return_value=None):
                commands._prefetch_certs()

        out = capsys.readouterr().out
        assert "Could not cache CA bundle for api.github.com" in out
        assert "Could not cache CA bundle for github.com" in out
        assert "Could not cache CA bundle for dev.azure.com" in out
        assert "Could not cache CA bundle for release-assets.githubusercontent.com" in out
        assert "Could not cache CA bundle for registry.npmjs.org" in out

    def test_writes_npmrc_when_npm_cert_cached(self, capsys, tmp_path):
        """Writes ~/.agdt/npmrc with cafile when npm registry cert is cached."""
        pem_path = str(tmp_path / "registry.npmjs.org.pem")
        npmrc_path = tmp_path / "npmrc"

        with patch.object(commands, "_ensure_ca_bundle", return_value=pem_path):
            with patch.object(commands, "_build_unified_ca_bundle", return_value=None):
                with patch.object(commands, "Path") as mock_path_cls:
                    mock_npmrc = mock_path_cls.home.return_value.__truediv__.return_value.__truediv__.return_value
                    mock_npmrc.parent = tmp_path
                    mock_npmrc.write_text = npmrc_path.write_text
                    commands._prefetch_certs()

        content = npmrc_path.read_text(encoding="utf-8")
        assert f"cafile={pem_path}" in content

    def test_prints_unified_bundle_hint_when_built(self, capsys, tmp_path):
        """Prints REQUESTS_CA_BUNDLE hint pointing at unified bundle when it is built."""
        pem_path = str(tmp_path / "some-host.pem")
        unified_path = tmp_path / "unified-ca-bundle.pem"
        unified_path.write_text("# placeholder\n", encoding="utf-8")

        with patch.object(commands, "_ensure_ca_bundle", return_value=pem_path):
            with patch.object(commands, "_build_unified_ca_bundle", return_value=unified_path):
                with patch.object(commands, "Path") as mock_path_cls:
                    mock_npmrc = mock_path_cls.home.return_value.__truediv__.return_value.__truediv__.return_value
                    mock_npmrc.parent = tmp_path
                    commands._prefetch_certs()

        out = capsys.readouterr().out
        assert f'REQUESTS_CA_BUNDLE="{unified_path}"' in out
        assert "bash/zsh" in out
        assert "PowerShell" in out
        assert "unified-ca-bundle.pem" in out

    def test_handles_exception_from_get_jira_base_url(self, capsys):
        """Does not raise when get_jira_base_url() raises; prints progress to stdout."""
        with patch.object(commands, "_ensure_ca_bundle", return_value=None):
            with patch.object(commands, "_build_unified_ca_bundle", return_value=None):
                with patch(
                    "agentic_devtools.cli.jira.config.get_jira_base_url",
                    side_effect=Exception("config error"),
                ):
                    # Should not raise
                    commands._prefetch_certs()

        out = capsys.readouterr().out
        assert "Fetching CA certificates" in out

    def test_no_pip_hint_when_no_unified_bundle(self, capsys, tmp_path):
        """Does not print REQUESTS_CA_BUNDLE hint when unified bundle could not be built."""
        with patch.object(commands, "_ensure_ca_bundle", return_value=None):
            with patch.object(commands, "_build_unified_ca_bundle", return_value=None):
                commands._prefetch_certs()

        out = capsys.readouterr().out
        assert "REQUESTS_CA_BUNDLE" not in out
