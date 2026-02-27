"""Tests for download_and_install (gh_cli_installer)."""

import io
import json
import tarfile
import zipfile
from unittest.mock import MagicMock, patch

import requests

from agentic_devtools.cli.setup import gh_cli_installer


def _make_tar_gz_bytes(binary_name: str, content: bytes) -> bytes:
    """Create an in-memory tar.gz archive with a bin/<binary> entry."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        info = tarfile.TarInfo(name=f"gh_2.65.0_linux_amd64/bin/{binary_name}")
        info.size = len(content)
        tar.addfile(info, io.BytesIO(content))
    return buf.getvalue()


def _make_zip_bytes(binary_name: str, content: bytes) -> bytes:
    """Create an in-memory zip archive with a bin/<binary> entry."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(f"gh_2.65.0_windows_amd64/bin/{binary_name}", content)
    return buf.getvalue()


def _make_zip_bytes_backslash(binary_name: str, content: bytes) -> bytes:
    """Create an in-memory zip archive with backslash-separated paths (Windows-style)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(f"gh_2.65.0_windows_amd64\\bin\\{binary_name}", content)
    return buf.getvalue()


def _make_zip_bytes_flat(binary_name: str, content: bytes) -> bytes:
    """Create an in-memory zip archive with a flat directory (no bin/ subdir)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(f"gh_2.87.3_windows_amd64/{binary_name}", content)
    return buf.getvalue()


def _make_mock_response(content: bytes) -> MagicMock:
    """Return a mock response that streams *content*."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.iter_content.return_value = [content]
    return mock_resp


class TestDownloadAndInstallGh:
    """Tests for download_and_install in gh_cli_installer."""

    def test_refuses_untrusted_host(self, tmp_path, capsys):
        """Returns False and prints an error for non-github.com URLs."""
        with patch.object(gh_cli_installer, "_INSTALL_DIR", tmp_path):
            with patch.object(gh_cli_installer, "_VERSION_FILE", tmp_path / "v.json"):
                result = gh_cli_installer.download_and_install(
                    "v2.65.0",
                    "https://evil.example.com/gh.tar.gz",
                    "gh_2.65.0_linux_amd64.tar.gz",
                )
        assert result is False
        assert "Refused" in capsys.readouterr().err

    def test_returns_false_on_request_error(self, tmp_path, capsys):
        """Returns False when the HTTP download fails."""
        with patch.object(gh_cli_installer, "_INSTALL_DIR", tmp_path):
            with patch.object(gh_cli_installer, "_VERSION_FILE", tmp_path / "v.json"):
                with patch("requests.get", side_effect=requests.ConnectionError("fail")):
                    result = gh_cli_installer.download_and_install(
                        "v2.65.0",
                        "https://github.com/releases/gh.tar.gz",
                        "gh_2.65.0_linux_amd64.tar.gz",
                    )
        assert result is False
        assert "Download failed" in capsys.readouterr().err

    def test_downloads_tar_and_extracts_binary(self, tmp_path):
        """Downloads a tar.gz, extracts gh binary, and records the version."""
        tar_content = _make_tar_gz_bytes("gh", b"gh-binary-content")
        mock_resp = _make_mock_response(tar_content)
        version_file = tmp_path / "v.json"
        with patch.object(gh_cli_installer, "_INSTALL_DIR", tmp_path):
            with patch.object(gh_cli_installer, "_VERSION_FILE", version_file):
                with patch.object(gh_cli_installer, "_BINARY_NAME", "gh"):
                    with patch("requests.get", return_value=mock_resp):
                        result = gh_cli_installer.download_and_install(
                            "v2.65.0",
                            "https://github.com/releases/gh.tar.gz",
                            "gh_2.65.0_linux_amd64.tar.gz",
                        )
        assert result is True
        written = (tmp_path / "gh").read_bytes()
        assert written == b"gh-binary-content"
        version_data = json.loads(version_file.read_text(encoding="utf-8"))
        assert version_data["version"] == "v2.65.0"

    def test_returns_false_when_binary_not_in_tar(self, tmp_path, capsys):
        """Returns False when the tar archive doesn't contain a gh binary."""
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            info = tarfile.TarInfo(name="something-else.txt")
            info.size = 5
            tar.addfile(info, io.BytesIO(b"hello"))
        tar_content = buf.getvalue()
        mock_resp = _make_mock_response(tar_content)
        with patch.object(gh_cli_installer, "_INSTALL_DIR", tmp_path):
            with patch.object(gh_cli_installer, "_VERSION_FILE", tmp_path / "v.json"):
                with patch.object(gh_cli_installer, "_BINARY_NAME", "gh"):
                    with patch("requests.get", return_value=mock_resp):
                        result = gh_cli_installer.download_and_install(
                            "v2.65.0",
                            "https://github.com/releases/gh.tar.gz",
                            "gh_2.65.0_linux_amd64.tar.gz",
                        )
        assert result is False
        assert "Could not find" in capsys.readouterr().err

    def test_downloads_zip_and_extracts_binary(self, tmp_path):
        """Downloads a zip, extracts gh binary, and records the version."""
        zip_content = _make_zip_bytes("gh.exe", b"gh-windows-binary")
        mock_resp = _make_mock_response(zip_content)
        version_file = tmp_path / "v.json"
        with patch.object(gh_cli_installer, "_INSTALL_DIR", tmp_path):
            with patch.object(gh_cli_installer, "_VERSION_FILE", version_file):
                with patch.object(gh_cli_installer, "_BINARY_NAME", "gh.exe"):
                    with patch("requests.get", return_value=mock_resp):
                        result = gh_cli_installer.download_and_install(
                            "v2.65.0",
                            "https://github.com/releases/gh.zip",
                            "gh_2.65.0_windows_amd64.zip",
                        )
        assert result is True
        version_data = json.loads(version_file.read_text(encoding="utf-8"))
        assert version_data["version"] == "v2.65.0"

    def test_downloads_zip_with_backslash_paths(self, tmp_path):
        """Extracts gh.exe from a zip archive with backslash-separated paths."""
        zip_content = _make_zip_bytes_backslash("gh.exe", b"gh-windows-binary")
        mock_resp = _make_mock_response(zip_content)
        version_file = tmp_path / "v.json"
        with patch.object(gh_cli_installer, "_INSTALL_DIR", tmp_path):
            with patch.object(gh_cli_installer, "_VERSION_FILE", version_file):
                with patch.object(gh_cli_installer, "_BINARY_NAME", "gh.exe"):
                    with patch("requests.get", return_value=mock_resp):
                        result = gh_cli_installer.download_and_install(
                            "v2.65.0",
                            "https://github.com/releases/gh.zip",
                            "gh_2.65.0_windows_amd64.zip",
                        )
        assert result is True
        written = (tmp_path / "gh.exe").read_bytes()
        assert written == b"gh-windows-binary"

    def test_returns_false_when_binary_not_in_zip(self, tmp_path, capsys):
        """Returns False when the zip archive doesn't contain a gh binary."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("readme.txt", "nothing here")
        zip_content = buf.getvalue()
        mock_resp = _make_mock_response(zip_content)
        with patch.object(gh_cli_installer, "_INSTALL_DIR", tmp_path):
            with patch.object(gh_cli_installer, "_VERSION_FILE", tmp_path / "v.json"):
                with patch.object(gh_cli_installer, "_BINARY_NAME", "gh"):
                    with patch("requests.get", return_value=mock_resp):
                        result = gh_cli_installer.download_and_install(
                            "v2.65.0",
                            "https://github.com/releases/gh.zip",
                            "gh_2.65.0_linux_amd64.zip",
                        )
        assert result is False
        err = capsys.readouterr().err
        assert "Could not find" in err
        assert "Archive contents:" in err

    def test_downloads_zip_flat_structure(self, tmp_path):
        """Extracts gh.exe from a zip with a flat directory (no bin/ subdir) as in newer releases."""
        zip_content = _make_zip_bytes_flat("gh.exe", b"gh-windows-binary-flat")
        mock_resp = _make_mock_response(zip_content)
        version_file = tmp_path / "v.json"
        with patch.object(gh_cli_installer, "_INSTALL_DIR", tmp_path):
            with patch.object(gh_cli_installer, "_VERSION_FILE", version_file):
                with patch.object(gh_cli_installer, "_BINARY_NAME", "gh.exe"):
                    with patch("requests.get", return_value=mock_resp):
                        result = gh_cli_installer.download_and_install(
                            "v2.87.3",
                            "https://github.com/releases/gh.zip",
                            "gh_2.87.3_windows_amd64.zip",
                        )
        assert result is True
        written = (tmp_path / "gh.exe").read_bytes()
        assert written == b"gh-windows-binary-flat"
        version_data = json.loads(version_file.read_text(encoding="utf-8"))
        assert version_data["version"] == "v2.87.3"

    def test_returns_false_on_tar_extraction_error(self, tmp_path, capsys):
        """Returns False when tar extraction raises an unexpected exception."""
        mock_resp = _make_mock_response(b"not-a-tar")
        with patch.object(gh_cli_installer, "_INSTALL_DIR", tmp_path):
            with patch.object(gh_cli_installer, "_VERSION_FILE", tmp_path / "v.json"):
                with patch.object(gh_cli_installer, "_BINARY_NAME", "gh"):
                    with patch("requests.get", return_value=mock_resp):
                        result = gh_cli_installer.download_and_install(
                            "v2.65.0",
                            "https://github.com/releases/gh.tar.gz",
                            "gh_2.65.0_linux_amd64.tar.gz",
                        )
        assert result is False
        assert "Extraction failed" in capsys.readouterr().err
