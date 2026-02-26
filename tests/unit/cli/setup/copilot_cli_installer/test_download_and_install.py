"""Tests for download_and_install (copilot_cli_installer)."""

import json
from unittest.mock import MagicMock, patch

import requests

from agentic_devtools.cli.setup import copilot_cli_installer


def _make_mock_response(content: bytes = b"binary-content") -> MagicMock:
    """Return a mock requests.Response that streams *content*."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.iter_content.return_value = [content]
    return mock_resp


class TestDownloadAndInstall:
    """Tests for download_and_install in copilot_cli_installer."""

    def test_refuses_untrusted_host(self, tmp_path, capsys):
        """Returns False and prints an error for non-github.com URLs."""
        with patch.object(copilot_cli_installer, "_INSTALL_DIR", tmp_path):
            with patch.object(copilot_cli_installer, "_VERSION_FILE", tmp_path / "v.json"):
                result = copilot_cli_installer.download_and_install(
                    "v1.0.0",
                    "https://evil.example.com/copilot",
                    "copilot-linux-amd64",
                )
        assert result is False
        captured = capsys.readouterr()
        assert "Refused" in captured.err

    def test_returns_false_on_request_error(self, tmp_path, capsys):
        """Returns False when the HTTP download fails."""
        with patch.object(copilot_cli_installer, "_INSTALL_DIR", tmp_path):
            with patch.object(copilot_cli_installer, "_VERSION_FILE", tmp_path / "v.json"):
                with patch("requests.get", side_effect=requests.ConnectionError("fail")):
                    result = copilot_cli_installer.download_and_install(
                        "v1.0.0",
                        "https://github.com/releases/copilot",
                        "copilot-linux-amd64",
                    )
        assert result is False
        captured = capsys.readouterr()
        assert "Download failed" in captured.err

    def test_downloads_and_writes_binary(self, tmp_path):
        """Successfully downloads, writes the binary, and records the version."""
        mock_resp = _make_mock_response(b"copilot-binary")
        version_file = tmp_path / "v.json"
        with patch.object(copilot_cli_installer, "_INSTALL_DIR", tmp_path):
            with patch.object(copilot_cli_installer, "_VERSION_FILE", version_file):
                with patch("requests.get", return_value=mock_resp):
                    result = copilot_cli_installer.download_and_install(
                        "v1.0.0",
                        "https://github.com/releases/copilot",
                        "copilot-linux-amd64",
                    )
        assert result is True
        binary_name = copilot_cli_installer._BINARY_NAME
        written = (tmp_path / binary_name).read_bytes()
        assert written == b"copilot-binary"
        version_data = json.loads(version_file.read_text(encoding="utf-8"))
        assert version_data["version"] == "v1.0.0"
        assert version_data["asset"] == "copilot-linux-amd64"

    def test_rejects_githubusercontent_domain(self, tmp_path, capsys):
        """Rejects download URLs from githubusercontent.com (only github.com is accepted)."""
        with patch.object(copilot_cli_installer, "_INSTALL_DIR", tmp_path):
            with patch.object(copilot_cli_installer, "_VERSION_FILE", tmp_path / "v.json"):
                result = copilot_cli_installer.download_and_install(
                    "v1.0.0",
                    "https://objects.githubusercontent.com/releases/copilot",
                    "copilot-linux-amd64",
                )
        # objects.githubusercontent.com is not github.com, should fail
        assert result is False
