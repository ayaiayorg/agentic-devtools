"""
GitHub Copilot CLI standalone binary installer.

Downloads and installs the ``copilot`` standalone binary from GitHub Releases
into ``~/.agdt/bin/``.  Tracks the installed version in
``~/.agdt/copilot-cli-version.json`` so that re-runs are idempotent.
"""

import io
import json
import platform
import shutil
import stat
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests

from agentic_devtools.cli.cert_utils import ssl_request_with_retry as _ssl_request_with_retry

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_RELEASES_URL = "https://api.github.com/repos/github/copilot-cli/releases/latest"
_INSTALL_DIR = Path.home() / ".agdt" / "bin"
_VERSION_FILE = Path.home() / ".agdt" / "copilot-cli-version.json"
_BINARY_NAME = "copilot.exe" if sys.platform == "win32" else "copilot"
_ALLOWED_DOWNLOAD_HOST = "github.com"


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def get_copilot_cli_binary() -> Optional[str]:
    """Return the path to the copilot binary, or ``None`` if not found.

    Checks (in order):
    1. The managed install location: ``~/.agdt/bin/copilot[.exe]``
    2. The system ``PATH`` (via :func:`shutil.which`).

    Returns:
        Absolute path string when found, ``None`` otherwise.
    """
    managed = _INSTALL_DIR / _BINARY_NAME
    if managed.is_file():
        return str(managed)
    return shutil.which("copilot")


def get_installed_version() -> Optional[str]:
    """Return the version string recorded in the version tracking file.

    Returns:
        Version string such as ``"v0.0.419"``, or ``None`` when the file
        does not exist or cannot be parsed.
    """
    if not _VERSION_FILE.exists():
        return None
    try:
        data: Dict[str, Any] = json.loads(_VERSION_FILE.read_text(encoding="utf-8"))
        return data.get("version")
    except (json.JSONDecodeError, OSError):
        return None


def get_latest_release_info() -> Dict[str, Any]:
    """Fetch the latest release metadata from the GitHub API.

    Returns:
        Parsed JSON response from the GitHub Releases API.

    Raises:
        requests.RequestException: On network or HTTP errors.
    """
    response = _ssl_request_with_retry(_RELEASES_URL, "api.github.com", timeout=30)
    response.raise_for_status()
    result: Dict[str, Any] = response.json()
    return result


def detect_platform_asset(assets: List[Dict[str, Any]]) -> str:
    """Select the release asset name that matches the current platform.

    Supported platforms:
    - Linux x86_64  → ``copilot-linux-amd64``
    - Linux aarch64 → ``copilot-linux-arm64``
    - macOS x86_64  → ``copilot-darwin-amd64``
    - macOS arm64   → ``copilot-darwin-arm64``
    - Windows x86_64 → ``copilot-win32-x64.zip``
    - Windows arm64  → ``copilot-win32-arm64.zip``

    Args:
        assets: List of asset dicts from the GitHub API (each has at least
            a ``"name"`` key).

    Returns:
        The ``name`` field of the matched asset.

    Raises:
        RuntimeError: When no asset matches the current platform/arch.
    """
    system = platform.system().lower()
    machine = platform.machine().lower()

    # Normalise arch names
    if machine in ("x86_64", "amd64"):
        arch = "amd64"
    elif machine in ("aarch64", "arm64"):
        arch = "arm64"
    else:
        raise RuntimeError(f"Unsupported architecture: {machine}")

    # Map system to asset platform name
    # Windows releases use "win32" prefix and "x64"/"arm64" arch naming in zip archives
    if system == "linux":
        target = f"copilot-linux-{arch}"
    elif system == "darwin":
        target = f"copilot-darwin-{arch}"
    elif system == "windows":
        win_arch = "x64" if arch == "amd64" else arch
        target = f"copilot-win32-{win_arch}.zip"
    else:
        raise RuntimeError(f"Unsupported operating system: {system}")

    asset_names = [a["name"] for a in assets]
    if target not in asset_names:
        raise RuntimeError(f"No release asset found for '{target}'. Available: {asset_names}")
    return target


def download_and_install(version: str, asset_url: str, asset_name: str) -> bool:
    """Download the binary from *asset_url* and install it into ``~/.agdt/bin/``.

    Security: verifies that the download URL is on the ``github.com`` domain
    before fetching.

    For zip archives (Windows), extracts the ``copilot.exe`` binary from the
    archive.  For bare binaries (Linux/macOS), writes the download directly.

    Args:
        version: Version string to record in the version file.
        asset_url: Direct URL to the binary asset (must be on ``github.com``).
        asset_name: Original asset filename (used in the version file and to
            determine whether extraction is needed).

    Returns:
        ``True`` on success, ``False`` on failure.
    """
    parsed = urlparse(asset_url)
    host = parsed.netloc.lower()
    if host != _ALLOWED_DOWNLOAD_HOST:
        print(
            f"  ✗ Refused to download from untrusted host: {host}",
            file=sys.stderr,
        )
        return False

    _INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    dest = _INSTALL_DIR / _BINARY_NAME

    try:
        response = _ssl_request_with_retry(asset_url, "github.com", timeout=120, stream=True)
        response.raise_for_status()
        asset_bytes = b"".join(response.iter_content(chunk_size=65536))
    except requests.RequestException as exc:
        print(f"  ✗ Download failed: {exc}", file=sys.stderr)
        return False

    if asset_name.endswith(".zip"):
        # Windows: extract copilot.exe from the zip archive
        try:
            with zipfile.ZipFile(io.BytesIO(asset_bytes)) as zf:
                extracted = False
                binary_basename = _BINARY_NAME.lower()
                for name in zf.namelist():
                    normalized = name.replace("\\", "/")
                    normalized_lower = normalized.lower()
                    if normalized_lower == binary_basename or normalized_lower.endswith(f"/{binary_basename}"):
                        dest.write_bytes(zf.read(name))
                        extracted = True
                        break
                if not extracted:
                    print(
                        f"  ✗ Could not find {_BINARY_NAME} inside archive '{asset_name}'",
                        file=sys.stderr,
                    )
                    return False
        except (zipfile.BadZipFile, KeyError, OSError) as exc:  # noqa: BLE001
            print(f"  ✗ Extraction failed: {exc}", file=sys.stderr)
            return False
    else:
        # Linux/macOS: the asset is the bare binary
        dest.write_bytes(asset_bytes)

    # Make executable on Unix-like systems
    if sys.platform != "win32":
        dest.chmod(dest.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    # Write version tracking file
    version_data = {
        "version": version,
        "installed_at": datetime.now(timezone.utc).isoformat(),
        "asset": asset_name,
    }
    _VERSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    _VERSION_FILE.write_text(json.dumps(version_data, indent=2), encoding="utf-8")

    return True


def install_copilot_cli(force: bool = False) -> bool:
    """Install the GitHub Copilot CLI standalone binary.

    Skips installation when the binary is already present and up-to-date
    unless *force* is ``True``.

    Args:
        force: When ``True``, reinstall even if already up-to-date.

    Returns:
        ``True`` when installed or already up-to-date, ``False`` on error.
    """
    print("Installing GitHub Copilot CLI...")

    existing = get_copilot_cli_binary()
    installed_version = get_installed_version()

    try:
        release = get_latest_release_info()
    except requests.RequestException as exc:
        print(f"  ✗ Failed to fetch release info: {exc}", file=sys.stderr)
        return False

    latest_version: str = release.get("tag_name", "")
    assets: List[Dict[str, Any]] = release.get("assets", [])

    if not force and existing and installed_version == latest_version:
        print(f"  ✓ Already up-to-date: copilot {installed_version}")
        return True

    try:
        asset_name = detect_platform_asset(assets)
    except RuntimeError as exc:
        print(f"  ✗ {exc}", file=sys.stderr)
        return False

    # Find the download URL for the matched asset
    asset_url: Optional[str] = None
    for asset in assets:
        if asset["name"] == asset_name:
            asset_url = asset.get("browser_download_url")
            break

    if not asset_url:
        print(f"  ✗ No download URL found for asset '{asset_name}'", file=sys.stderr)
        return False

    ok = download_and_install(latest_version, asset_url, asset_name)
    if ok:
        install_path = str(_INSTALL_DIR / _BINARY_NAME)
        print(f"  ✓ Downloaded copilot {latest_version} for {_get_platform_label()}")
        print(f"  ✓ Installed to {install_path}")
    return ok


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_platform_label() -> str:
    """Return a human-readable platform/arch label (e.g. ``linux-amd64``)."""
    system = platform.system().lower()
    machine = platform.machine().lower()
    arch = "arm64" if machine in ("aarch64", "arm64") else "amd64"
    return f"{system}-{arch}"
