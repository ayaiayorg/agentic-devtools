"""Generator for ``agentic-devtools-required-setup.py``.

The generated script uses **only** the Python standard library.  It
detects and removes corrupted installation artefacts, then installs the
latest PyPI release of ``agentic-devtools``.
"""

from __future__ import annotations

import site
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Corruption detection helpers (used by the generator to embed logic)
# ---------------------------------------------------------------------------


def detect_corrupted_artifacts() -> list[Path]:
    """Scan site-packages for known corrupted agentic-devtools artefacts.

    Returns a list of filesystem paths that should be removed before a
    clean install can succeed.

    Detected artefact patterns:
    * Directories named ``~gentic-devtools`` or ``~gentic_devtools``
      (leftover from interrupted pip uninstalls).
    * ``.dist-info`` directories for ``agentic-devtools`` / ``agentic_devtools``
      that lack a ``RECORD`` file.
    * ``_editable_impl_agentic_devtools.pth`` files (leftovers from
      editable installs).
    """
    artifacts: list[Path] = []

    for sp_dir in _site_packages_dirs():
        sp = Path(sp_dir)
        if not sp.is_dir():
            continue

        try:
            children = list(sp.iterdir())
        except (PermissionError, OSError):
            continue

        for child in children:
            name = child.name

            # Tilde-prefixed leftover directories
            if child.is_dir() and name in {"~gentic-devtools", "~gentic_devtools"}:
                artifacts.append(child)
                continue

            # dist-info without RECORD
            if (
                child.is_dir()
                and name.endswith(".dist-info")
                and ("agentic-devtools" in name or "agentic_devtools" in name)
            ):
                record = child / "RECORD"
                if not record.exists():
                    artifacts.append(child)
                continue

            # Editable-install .pth files
            if child.is_file() and name == "_editable_impl_agentic_devtools.pth":
                artifacts.append(child)

    return artifacts


def cleanup_artifacts(artifacts: list[Path]) -> list[str]:
    """Remove the artefacts returned by :func:`detect_corrupted_artifacts`.

    Returns a list of human-readable messages describing each removal
    attempt (success or failure).
    """
    import shutil

    messages: list[str] = []
    for artifact in artifacts:
        try:
            if artifact.is_symlink():
                artifact.unlink()
            elif artifact.is_dir():
                shutil.rmtree(artifact)
            else:
                artifact.unlink()
            messages.append(f"  Removed: {artifact}")
        except PermissionError:
            messages.append(f"  ⚠ Permission denied (read-only site-packages?): {artifact}")
        except OSError as exc:
            messages.append(f"  ⚠ Failed to remove {artifact}: {exc}")
    return messages


def install_package() -> tuple[bool, str]:
    """Install/upgrade ``agentic-devtools`` from PyPI.

    Returns ``(success, output)`` where *output* is the combined
    stdout + stderr from pip.
    """
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", "agentic-devtools"],
        capture_output=True,
        text=True,
    )
    output = (result.stdout + "\n" + result.stderr).strip()
    return result.returncode == 0, output


def setup_git_hooks() -> str | None:
    """Configure ``core.hooksPath`` to ``.githooks`` if inside a git repo.

    Returns a status message, or ``None`` when not in a git context.
    """
    # Check if we're in a git repo
    try:
        subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None

    # Check current hooksPath
    try:
        result = subprocess.run(
            ["git", "config", "--get", "core.hooksPath"],
            capture_output=True,
            text=True,
        )
        current = result.stdout.strip() if result.returncode == 0 else ""
    except FileNotFoundError:
        return None

    warning: str | None = None
    if current and current != ".githooks":
        warning = f"  ⚠ core.hooksPath is already set to '{current}' (not '.githooks'). Overwriting."

    try:
        subprocess.run(
            ["git", "config", "core.hooksPath", ".githooks"],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        return f"  ⚠ Failed to set core.hooksPath: {exc}"

    # Ensure .githooks directory exists
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        hooks_dir = Path(result.stdout.strip()) / ".githooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
    except (subprocess.CalledProcessError, OSError):
        pass

    if warning:
        return warning + "\n  ✓ core.hooksPath set to '.githooks'"
    return "  ✓ core.hooksPath set to '.githooks'"


# ---------------------------------------------------------------------------
# Script content generator
# ---------------------------------------------------------------------------


def generate_required_setup_script() -> str:
    """Return the full content of ``agentic-devtools-required-setup.py``.

    The generated script is stdlib-only and supports a ``--foreground``
    flag (currently a no-op for forward compatibility).
    """
    return _REQUIRED_SETUP_TEMPLATE


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _site_packages_dirs() -> list[str]:
    """Return a list of site-packages directories for the current interpreter."""
    dirs: list[str] = []
    for attr in ("getsitepackages", "getusersitepackages"):
        fn = getattr(site, attr, None)
        if fn is None:
            continue
        result = fn()
        if isinstance(result, str):
            dirs.append(result)
        elif isinstance(result, list):
            dirs.extend(result)
    return dirs


# ---------------------------------------------------------------------------
# Template — the generated script that goes into .agdt/
# ---------------------------------------------------------------------------

_REQUIRED_SETUP_TEMPLATE = '''\
#!/usr/bin/env python3
"""agentic-devtools required setup — self-repair & install.

This script is managed by agentic-devtools and regenerated on every
``agdt-setup`` run.  DO NOT EDIT — your changes will be overwritten.

Supports: ``--foreground`` (default, forward-compatible no-op).
"""

import argparse
import shutil
import site
import subprocess
import sys
from pathlib import Path


def _site_packages_dirs():
    """Return site-packages directories."""
    dirs = []
    for attr in ("getsitepackages", "getusersitepackages"):
        fn = getattr(site, attr, None)
        if fn is None:
            continue
        result = fn()
        if isinstance(result, str):
            dirs.append(result)
        elif isinstance(result, list):
            dirs.extend(result)
    return dirs


def _detect_corrupted_artifacts():
    """Scan site-packages for corrupted agentic-devtools artefacts."""
    artifacts = []
    for sp_dir in _site_packages_dirs():
        sp = Path(sp_dir)
        if not sp.is_dir():
            continue
        try:
            children = list(sp.iterdir())
        except (PermissionError, OSError):
            continue
        for child in children:
            name = child.name
            if child.is_dir() and name in {"~gentic-devtools", "~gentic_devtools"}:
                artifacts.append(child)
                continue
            if (
                child.is_dir()
                and name.endswith(".dist-info")
                and ("agentic-devtools" in name or "agentic_devtools" in name)
            ):
                if not (child / "RECORD").exists():
                    artifacts.append(child)
                continue
            if child.is_file() and name == "_editable_impl_agentic_devtools.pth":
                artifacts.append(child)
    return artifacts


def _cleanup_artifacts(artifacts):
    """Remove corrupted artefacts with permission error handling."""
    for artifact in artifacts:
        try:
            if artifact.is_symlink():
                artifact.unlink()
            elif artifact.is_dir():
                shutil.rmtree(artifact)
            else:
                artifact.unlink()
            print(f"  Removed: {artifact}")
        except PermissionError:
            print(f"  ⚠ Permission denied (read-only site-packages?): {artifact}")
        except OSError as exc:
            print(f"  ⚠ Failed to remove {artifact}: {exc}")


def _install_package():
    """Install/upgrade agentic-devtools from PyPI."""
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", "agentic-devtools"],
        capture_output=False,
    )
    return result.returncode == 0


def _setup_git_hooks():
    """Configure core.hooksPath to .githooks if in a git repo."""
    try:
        subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True, text=True, check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("  ℹ Not a git repository — skipping git hooks setup.")
        return

    try:
        result = subprocess.run(
            ["git", "config", "--get", "core.hooksPath"],
            capture_output=True, text=True,
        )
        current = result.stdout.strip() if result.returncode == 0 else ""
    except FileNotFoundError:
        return

    if current and current != ".githooks":
        print(
            f"  ⚠ core.hooksPath is already set to \\'{current}\\' "
            "(not \\'.githooks\\'). Overwriting."
        )

    try:
        subprocess.run(
            ["git", "config", "core.hooksPath", ".githooks"],
            capture_output=True, text=True, check=True,
        )
        print("  ✓ core.hooksPath set to \\'.githooks\\'")
    except subprocess.CalledProcessError as exc:
        print(f"  ⚠ Failed to set core.hooksPath: {exc}")
        return

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        hooks_dir = Path(result.stdout.strip()) / ".githooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
    except (subprocess.CalledProcessError, OSError):
        pass


def main():
    parser = argparse.ArgumentParser(
        description="agentic-devtools required setup — self-repair & install.",
    )
    parser.add_argument(
        "--foreground", action="store_true", default=True,
        help="Run in foreground (default, forward-compatible).",
    )
    parser.parse_args()

    print("─── agentic-devtools Required Setup ─────────────────────────")
    print()

    # Step 1: Detect corrupted artefacts
    print("Scanning for corrupted installation artefacts...")
    artifacts = _detect_corrupted_artifacts()
    if artifacts:
        print(f"  Found {len(artifacts)} corrupted artefact(s):")
        for a in artifacts:
            print(f"    - {a}")
        print()
        print("Cleaning up...")
        _cleanup_artifacts(artifacts)
        print()
    else:
        print("  ✓ No corrupted artefacts detected.")
        print()

    # Step 2: Install/upgrade
    print("Installing/upgrading agentic-devtools from PyPI...")
    if _install_package():
        print("  ✓ agentic-devtools installed/upgraded successfully.")
    else:
        print("  ✗ Failed to install agentic-devtools.", file=sys.stderr)
        sys.exit(1)
    print()

    # Step 3: Git hooks
    print("Configuring git hooks...")
    _setup_git_hooks()
    print()

    print("─── Required Setup Complete ─────────────────────────────────")


if __name__ == "__main__":
    main()
'''
