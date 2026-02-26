"""
Unified dependency checker for agentic-devtools.

Checks all external CLI tools that ``agentic-devtools`` depends on and
reports their availability, version, and install path in a formatted table.
"""

import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from ..subprocess_utils import run_safe

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MANAGED_BIN_DIR = Path.home() / ".agdt" / "bin"


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------


@dataclass
class DependencyStatus:
    """Status of a single external CLI dependency.

    Attributes:
        name: The binary name (e.g. ``"git"``, ``"gh"``).
        found: Whether the binary was located.
        path: Absolute path to the binary when *found* is ``True``.
        version: Version string extracted from the binary, or ``None``.
        required: Whether the tool is strictly required for core functionality.
        install_hint: Short hint shown in the report when the tool is missing.
        category: Human-readable category label (``"Required"``, ``"Recommended"``,
            or ``"Optional — ..."``) used for display.
    """

    name: str
    found: bool
    path: Optional[str] = field(default=None)
    version: Optional[str] = field(default=None)
    required: bool = field(default=False)
    install_hint: str = field(default="")
    category: str = field(default="Optional")


# ---------------------------------------------------------------------------
# Version extractors
# ---------------------------------------------------------------------------


def _run_version(args: List[str]) -> Optional[str]:
    """Run *args* and return the first non-empty line of stdout.

    Uses ``shell=None`` so that :func:`run_safe` applies its default
    Windows behaviour (``shell=True`` for list args), which is needed for
    tools like ``az`` and ``code`` that are ``.cmd`` shims on Windows.
    The args here are never user-controlled, so this is safe.

    Returns ``None`` on any error or non-zero exit code.
    """
    try:
        result = run_safe(args, capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().splitlines()[0]
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def _get_version(name: str, path: str) -> Optional[str]:
    """Return a version string for *name* at *path*, or ``None``."""
    if name == "git":
        raw = _run_version([path, "--version"])
        # "git version 2.43.0" → "2.43.0"
        if raw and raw.startswith("git version "):
            return raw[len("git version ") :].strip()
        return raw
    if name in ("gh", "copilot"):
        raw = _run_version([path, "--version"])
        if raw:
            # "gh version 2.65.0 (2025-01-01)" → "2.65.0"
            parts = raw.split()
            for i, part in enumerate(parts):
                if part == "version" and i + 1 < len(parts):
                    return parts[i + 1]
            # Fallback: return first token that looks like a version
            for part in parts:
                if part and (part[0].isdigit() or part.startswith("v")):
                    return part
        return raw
    if name == "az":
        raw = _run_version([path, "--version"])
        if raw:
            # "azure-cli  2.57.0" → "2.57.0"
            parts = raw.split()
            for part in parts:
                if part and (part[0].isdigit() or part.startswith("v")):
                    return part
        return raw
    if name == "code":
        return _run_version([path, "--version"])
    return _run_version([path, "--version"])


# ---------------------------------------------------------------------------
# Dependency definitions
# ---------------------------------------------------------------------------


def _find_binary(name: str) -> Optional[str]:
    """Locate *name* in the managed bin dir first, then on ``PATH``."""
    managed = _MANAGED_BIN_DIR / (name + (".exe" if sys.platform == "win32" else ""))
    if managed.is_file():
        return str(managed)
    return shutil.which(name)


def _check_dependency(
    name: str,
    *,
    required: bool,
    install_hint: str,
    category: str,
) -> DependencyStatus:
    """Check a single dependency and return its :class:`DependencyStatus`."""
    path = _find_binary(name)
    if not path:
        return DependencyStatus(
            name=name,
            found=False,
            required=required,
            install_hint=install_hint,
            category=category,
        )
    version = _get_version(name, path)
    return DependencyStatus(
        name=name,
        found=True,
        path=path,
        version=version,
        required=required,
        install_hint=install_hint,
        category=category,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def check_all_dependencies() -> List[DependencyStatus]:
    """Check all external CLI dependencies.

    Returns:
        A list of :class:`DependencyStatus` objects, one per tool.
    """
    return [
        _check_dependency(
            "copilot",
            required=False,
            install_hint="run: agdt-setup-copilot-cli",
            category="Recommended",
        ),
        _check_dependency(
            "gh",
            required=False,
            install_hint="run: agdt-setup-gh-cli  (or https://cli.github.com/)",
            category="Recommended",
        ),
        _check_dependency(
            "git",
            required=True,
            install_hint="https://git-scm.com/downloads",
            category="Required",
        ),
        _check_dependency(
            "az",
            required=False,
            install_hint="https://docs.microsoft.com/cli/azure/install-azure-cli",
            category="Optional — needed for Azure DevOps",
        ),
        _check_dependency(
            "code",
            required=False,
            install_hint="https://code.visualstudio.com/",
            category="Optional — needed for VS Code integration",
        ),
    ]


def print_dependency_report(statuses: List[DependencyStatus]) -> None:
    """Pretty-print a dependency status table to stdout.

    Args:
        statuses: List of :class:`DependencyStatus` objects to display.
    """
    print("\nDependency Check:")

    name_width = max(len(s.name) for s in statuses) + 2
    version_width = 10

    for s in statuses:
        icon = "✅" if s.found else "❌"
        name = s.name.ljust(name_width)
        version = (s.version or "—").ljust(version_width)
        location = s.path if s.path else "not found"
        category = s.category
        line = f"  {icon} {name}{version}  {location:<40}  ({category})"
        print(line)
        if not s.found and s.install_hint:
            print(f"       Install: {s.install_hint}")
