"""Tests for setup_certs_cmd."""

import os
from unittest.mock import patch

from agentic_devtools.cli.setup import commands


class TestSetupCertsCmd:
    """Tests for setup_certs_cmd."""

    def test_calls_prefetch_certs(self, capsys):
        """Calls _prefetch_certs to refresh certificate bundles."""
        with patch("sys.argv", ["agdt-setup-certs"]):
            with patch.object(commands, "_prefetch_certs") as mock_prefetch:
                with patch.object(commands, "_persist_env_vars_to_profile"):
                    commands.setup_certs_cmd()
        mock_prefetch.assert_called_once()

    def test_prints_refreshing_message(self, capsys):
        """Prints a 'Refreshing' banner before running prefetch."""
        with patch("sys.argv", ["agdt-setup-certs"]):
            with patch.object(commands, "_prefetch_certs"):
                with patch.object(commands, "_persist_env_vars_to_profile"):
                    commands.setup_certs_cmd()
        out = capsys.readouterr().out
        assert "Refreshing" in out

    def test_no_persist_env_flag_accepted(self, capsys):
        """Accepts --no-persist-env flag."""
        with patch("sys.argv", ["agdt-setup-certs", "--no-persist-env"]):
            with patch.object(commands, "_prefetch_certs"):
                with patch.object(commands, "_persist_env_vars_to_profile") as mock_persist:
                    commands.setup_certs_cmd()
        mock_persist.assert_called_once()
        assert mock_persist.call_args.kwargs["persist_env"] is False

    def test_overwrite_env_flag_accepted(self, capsys):
        """Accepts --overwrite-env flag."""
        with patch("sys.argv", ["agdt-setup-certs", "--overwrite-env"]):
            with patch.object(commands, "_prefetch_certs"):
                with patch.object(commands, "_persist_env_vars_to_profile") as mock_persist:
                    commands.setup_certs_cmd()
        mock_persist.assert_called_once()
        assert mock_persist.call_args.kwargs["overwrite_env"] is True

    def test_no_verify_ssl_sets_env_var(self, monkeypatch, capsys):
        """Sets AGDT_NO_VERIFY_SSL env var when --no-verify-ssl is passed."""
        monkeypatch.delenv("AGDT_NO_VERIFY_SSL", raising=False)
        with patch("sys.argv", ["agdt-setup-certs", "--no-verify-ssl"]):
            with patch.object(commands, "_prefetch_certs"):
                with patch.object(commands, "_persist_env_vars_to_profile"):
                    commands.setup_certs_cmd()
        assert os.environ.get("AGDT_NO_VERIFY_SSL") == "1"
        out = capsys.readouterr().out
        assert "SSL verification disabled" in out
