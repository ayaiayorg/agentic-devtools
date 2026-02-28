"""
GitHub CLI (gh) installer.

Downloads and installs the ``gh`` binary from GitHub Releases into
``~/.agdt/bin/``.  Tracks the installed version in
``~/.agdt/gh-cli-version.json`` so that re-runs are idempotent.
"""

import json
import platform
import shutil
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests

from agentic_devtools.cli.cert_utils import ssl_request_with_retry as _ssl_request_with_retry

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_RELEASES_URL = "https://api.github.com/repos/cli/cli/releases/latest"
_INSTALL_DIR = Path.home() / ".agdt" / "bin"
_VERSION_FILE = Path.home() / ".agdt" / "gh-cli-version.json"
_BINARY_NAME = "gh.exe" if sys.platform == "win32" else "gh"
_ALLOWED_DOWNLOAD_HOST = "github.com"


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def get_gh_cli_binary() -> Optional[str]:
    """Return the path to the ``gh`` binary, or ``None`` if not found.

    Checks (in order):
    1. The managed install location: ``~/.agdt/bin/gh[.exe]``
    2. The system ``PATH`` (via :func:`shutil.which`).

    Returns:
        Absolute path string when found, ``None`` otherwise.
    """
    managed = _INSTALL_DIR / _BINARY_NAME
    if managed.is_file():
        return str(managed)
    return shutil.which("gh")


def get_installed_version() -> Optional[str]:
    """Return the version string recorded in the version tracking file.

    Returns:
        Version string such as ``"v2.65.0"``, or ``None`` when the file
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
    """Select the release asset that matches the current platform.

    The ``gh`` CLI distributes platform-specific archives.  This function
    selects the correct tarball/zip name for the current OS and architecture.

    Supported platforms:
    - Linux x86_64  → ``gh_*_linux_amd64.tar.gz``
    - Linux aarch64 → ``gh_*_linux_arm64.tar.gz``
    - macOS x86_64  → ``gh_*_macOS_amd64.zip``
    - macOS arm64   → ``gh_*_macOS_arm64.zip``
    - Windows x86_64 → ``gh_*_windows_amd64.zip``

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

    # Map system to expected patterns in asset names
    asset_names = [a["name"] for a in assets]

    if system == "linux":
        suffix = ".tar.gz"
        os_fragment = "linux"
    elif system == "darwin":
        suffix = ".zip"
        os_fragment = "macOS"
    elif system == "windows":
        suffix = ".zip"
        os_fragment = "windows"
    else:
        raise RuntimeError(f"Unsupported operating system: {system}")

    for name in asset_names:
        # Match pattern: gh_VERSION_OSFRAGMENT_ARCH.SUFFIX
        if f"_{os_fragment}_{arch}" in name and name.endswith(suffix):
            return name

    raise RuntimeError(f"No release asset found for {system}/{arch}{suffix}. Available: {asset_names}")


def download_and_install(version: str, asset_url: str, asset_name: str) -> bool:
    """Download the ``gh`` archive from *asset_url* and extract the binary.

    Security: verifies that the download URL is on the ``github.com`` domain
    before fetching.

    The archive is downloaded to a temporary path, the ``gh`` binary is
    extracted from it, and then moved to ``~/.agdt/bin/``.

    Args:
        version: Version string to record in the version file.
        asset_url: Direct URL to the archive asset (must be on ``github.com``).
        asset_name: Original asset filename (used to determine archive type and
            for the version file).

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

    import tarfile
    import tempfile
    import zipfile

    try:
        response = _ssl_request_with_retry(asset_url, "github.com", timeout=120, stream=True)
        response.raise_for_status()

        with tempfile.TemporaryDirectory() as tmp_dir:
            archive_path = Path(tmp_dir) / asset_name
            with archive_path.open("wb") as fh:
                for chunk in response.iter_content(chunk_size=65536):
                    fh.write(chunk)

            gh_binary = _BINARY_NAME
            dest = _INSTALL_DIR / gh_binary

            if asset_name.endswith(".tar.gz"):
                with tarfile.open(archive_path) as tar:
                    # gh archives have structure: gh_VERSION_os_arch/bin/gh
                    extracted = False
                    for member in tar.getmembers():
                        if member.name.endswith("/bin/gh") or member.name == "gh":
                            member.name = gh_binary
                            # Safe: archive source is verified as github.com and we
                            # select a single, name-validated member (no path traversal).
                            tar.extract(member, path=tmp_dir)  # noqa: S202
                            Path(tmp_dir, gh_binary).replace(dest)
                            extracted = True
                            break
                    if not extracted:
                        print(
                            f"  ✗ Could not find gh binary inside archive '{asset_name}'",
                            file=sys.stderr,
                        )
                        return False
            else:
                # .zip archive
                with zipfile.ZipFile(archive_path) as zf:
                    extracted = False
                    entries = zf.namelist()
                    for name in entries:
                        normalized = name.replace("\\", "/")
                        if normalized.endswith(f"/{gh_binary}") or normalized == gh_binary:
                            data = zf.read(name)
                            dest.write_bytes(data)
                            extracted = True
                            break
                    if not extracted:
                        print(
                            f"  ✗ Could not find gh binary inside archive '{asset_name}'",
                            file=sys.stderr,
                        )
                        print(
                            f"  ✗ Archive contents: {entries}",
                            file=sys.stderr,
                        )
                        return False

    except requests.RequestException as exc:
        print(f"  ✗ Download failed: {exc}", file=sys.stderr)
        return False
    except (tarfile.TarError, Exception) as exc:  # noqa: BLE001
        print(f"  ✗ Extraction failed: {exc}", file=sys.stderr)
        return False

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


def install_gh_cli(force: bool = False) -> bool:
    """Install the GitHub CLI (``gh``) binary.

    Skips installation when the binary is already present and up-to-date
    unless *force* is ``True``.

    Args:
        force: When ``True``, reinstall even if already up-to-date.

    Returns:
        ``True`` when installed or already up-to-date, ``False`` on error.
    """
    print("Installing GitHub CLI (gh)...")

    existing = get_gh_cli_binary()
    installed_version = get_installed_version()

    try:
        release = get_latest_release_info()
    except requests.RequestException as exc:
        print(f"  ✗ Failed to fetch release info: {exc}", file=sys.stderr)
        return False

    latest_version: str = release.get("tag_name", "")
    assets: List[Dict[str, Any]] = release.get("assets", [])

    if not force and existing and installed_version == latest_version:
        print(f"  ✓ Already up-to-date: gh {installed_version}")
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
        print(f"  ✓ Downloaded gh {latest_version} for {_get_platform_label()}")
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
