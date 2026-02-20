"""Helper utilities for PyPI release flows."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from agentic_devtools.cli.subprocess_utils import run_safe


@dataclass(frozen=True)
class PackageArtifact:
    """Represents a built package artifact."""

    filename: str
    version: str
    sha256: str
    size_bytes: int
    dist_path: str


class ReleaseError(RuntimeError):
    """Raised when a release step fails."""


def _get_requests():
    """Lazy import for requests to keep helpers lightweight."""
    try:
        import requests
    except ImportError as exc:  # pragma: no cover - defensive branch
        raise ImportError("requests library required. Install with: pip install requests") from exc
    return requests


def normalize_package_name(name: str) -> str:
    """Normalize a package name according to PEP 503."""
    normalized = re.sub(r"[-_.]+", "-", name).lower()
    return normalized.strip("-")


def pypi_version_exists(package_name: str, version: str, *, repository: str = "pypi") -> bool:
    """Check whether a version exists on PyPI/TestPyPI."""
    repo = repository.lower()
    if repo not in {"pypi", "testpypi"}:
        raise ValueError(f"Unsupported repository: {repository}")
    base_url = "https://test.pypi.org/pypi" if repo == "testpypi" else "https://pypi.org/pypi"
    normalized = normalize_package_name(package_name)
    url = f"{base_url}/{normalized}/{version}/json"
    requests = _get_requests()
    try:
        response = requests.get(url, timeout=10)
    except Exception as exc:  # pragma: no cover - network failure
        raise ReleaseError(f"PyPI version check failed: {exc}") from exc
    if response.status_code == 200:
        return True
    if response.status_code == 404:
        return False
    raise ReleaseError(f"PyPI version check failed with status {response.status_code}")


def build_distribution(dist_dir: str = "dist") -> None:
    """Build wheel/sdist into the dist directory."""
    result = run_safe(
        ["python", "-m", "build", "--outdir", dist_dir],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise ReleaseError(f"Build failed: {result.stderr or result.stdout}")


def validate_distribution(dist_dir: str = "dist") -> None:
    """Run twine check on built artifacts."""
    pattern = str(Path(dist_dir) / "*")
    result = run_safe(
        ["python", "-m", "twine", "check", pattern],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise ReleaseError(f"Twine check failed: {result.stderr or result.stdout}")


def upload_distribution(dist_dir: str = "dist", *, repository: Optional[str] = None) -> None:
    """Upload built artifacts with twine."""
    pattern = str(Path(dist_dir) / "*")
    args = ["python", "-m", "twine", "upload"]
    if repository:
        args.extend(["--repository", repository])
    args.append(pattern)
    result = run_safe(args, capture_output=True, text=True)
    if result.returncode != 0:
        raise ReleaseError(f"Twine upload failed: {result.stderr or result.stdout}")


def compute_sha256(path: Path) -> str:
    """Compute SHA256 hash for a file."""
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()
