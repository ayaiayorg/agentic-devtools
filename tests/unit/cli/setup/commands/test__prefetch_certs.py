"""Tests for _prefetch_certs."""

from unittest.mock import patch

import pytest

from agentic_devtools.cli.setup import commands


@pytest.fixture(autouse=True)
def mock_setup_network():
    """Override the conftest autouse mock to test _prefetch_certs directly."""
    with patch("agentic_devtools.cli.setup.gh_cli_installer._get_ssl_verify", return_value=True):
        with patch("agentic_devtools.cli.setup.copilot_cli_installer._get_ssl_verify", return_value=True):
            yield


class TestPrefetchCerts:
    """Tests for _prefetch_certs."""

    def test_prints_cached_message_when_bundles_exist(self, capsys, tmp_path):
        """Prints cached messages when ensure_ca_bundle returns paths."""
        pem_path = str(tmp_path / "cert.pem")

        with patch.object(commands, "_ensure_ca_bundle", return_value=pem_path):
            with patch.object(commands, "Path") as mock_path_cls:
                mock_npmrc = mock_path_cls.home.return_value.__truediv__.return_value.__truediv__.return_value
                mock_npmrc.parent = tmp_path
                commands._prefetch_certs()

        out = capsys.readouterr().out
        assert "CA bundle cached for api.github.com" in out
        assert "CA bundle cached for github.com" in out
        assert "CA bundle cached for registry.npmjs.org" in out

    def test_prints_warning_message_when_bundles_missing(self, capsys):
        """Prints warning messages when ensure_ca_bundle returns None."""
        with patch.object(commands, "_ensure_ca_bundle", return_value=None):
            commands._prefetch_certs()

        out = capsys.readouterr().out
        assert "Could not cache CA bundle for api.github.com" in out
        assert "Could not cache CA bundle for github.com" in out
        assert "Could not cache CA bundle for registry.npmjs.org" in out

    def test_writes_npmrc_when_npm_cert_cached(self, capsys, tmp_path):
        """Writes ~/.agdt/npmrc with cafile when npm registry cert is cached."""
        pem_path = str(tmp_path / "registry.npmjs.org.pem")
        npmrc_path = tmp_path / "npmrc"

        with patch.object(commands, "_ensure_ca_bundle", return_value=pem_path):
            with patch.object(commands, "Path") as mock_path_cls:
                mock_npmrc = mock_path_cls.home.return_value.__truediv__.return_value.__truediv__.return_value
                mock_npmrc.parent = tmp_path
                mock_npmrc.write_text = npmrc_path.write_text
                commands._prefetch_certs()

        content = npmrc_path.read_text(encoding="utf-8")
        assert f"cafile={pem_path}" in content

    def test_prints_pip_hint_when_github_cert_cached(self, capsys, tmp_path):
        """Prints REQUESTS_CA_BUNDLE hint when api.github.com cert is cached."""
        pem_path = str(tmp_path / "api.github.com.pem")

        with patch.object(commands, "_ensure_ca_bundle", return_value=pem_path):
            with patch.object(commands, "Path") as mock_path_cls:
                mock_npmrc = mock_path_cls.home.return_value.__truediv__.return_value.__truediv__.return_value
                mock_npmrc.parent = tmp_path
                commands._prefetch_certs()

        out = capsys.readouterr().out
        assert f'REQUESTS_CA_BUNDLE="{pem_path}"' in out
        assert "bash/zsh" in out
        assert "PowerShell" in out
