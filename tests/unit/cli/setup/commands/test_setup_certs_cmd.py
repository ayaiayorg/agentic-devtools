"""Tests for setup_certs_cmd."""

from unittest.mock import patch

from agentic_devtools.cli.setup import commands


class TestSetupCertsCmd:
    """Tests for setup_certs_cmd."""

    def test_calls_prefetch_certs(self, capsys):
        """Calls _prefetch_certs to refresh certificate bundles."""
        with patch.object(commands, "_prefetch_certs") as mock_prefetch:
            commands.setup_certs_cmd()
        mock_prefetch.assert_called_once()

    def test_prints_refreshing_message(self, capsys):
        """Prints a 'Refreshing' banner before running prefetch."""
        with patch.object(commands, "_prefetch_certs"):
            commands.setup_certs_cmd()
        out = capsys.readouterr().out
        assert "Refreshing" in out
