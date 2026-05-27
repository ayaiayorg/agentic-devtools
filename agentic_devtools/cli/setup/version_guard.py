"""Version guard for agdt-setup.

Compares the running ``agentic-devtools`` version against the version
pinned in ``.agdt/config/project.json`` (key ``agdt_version``) and
decides whether setup should proceed, be blocked, or run in
local-only (force) mode.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def _fallback_compare(running: str, pinned: str) -> int:
    """Segment-based version comparison fallback.

    Used when ``packaging`` is unavailable or when versions cannot be
    parsed as PEP 440.  Strips ``+local`` metadata, splits on ``'.'``,
    pads shorter segments with ``0``, then compares segment-by-segment.

    Returns ``-1`` (running < pinned), ``0`` (equal), or ``1``
    (running > pinned).  On any unexpected error, returns ``0``
    (fail-open).
    """
    try:
        # Strip +local metadata
        running = re.sub(r"\+.*$", "", running.strip())
        pinned = re.sub(r"\+.*$", "", pinned.strip())

        if not running or not pinned:
            return 0  # fail-open

        r_parts = running.split(".")
        p_parts = pinned.split(".")

        # Pad shorter list with "0"
        max_len = max(len(r_parts), len(p_parts))
        r_parts.extend(["0"] * (max_len - len(r_parts)))
        p_parts.extend(["0"] * (max_len - len(p_parts)))

        for r_seg, p_seg in zip(r_parts, p_parts):
            r_val = _segment_value(r_seg)
            p_val = _segment_value(p_seg)
            if r_val < p_val:
                return -1
            if r_val > p_val:
                return 1
        return 0
    except Exception:  # noqa: BLE001
        return 0  # fail-open


def _segment_value(segment: str) -> tuple[int, int, int]:
    """Convert a version segment to a comparable tuple.

    Pure numeric segments sort higher than segments with pre-release
    suffixes (``dev``, ``alpha``, ``beta``, ``rc``).  Post-release
    (``post``) sorts above the base version.

    Returns ``(numeric_part, suffix_order, suffix_number)`` where
    suffix_order is:
    - ``-4`` for ``dev``
    - ``-3`` for ``alpha`` / ``a``
    - ``-2`` for ``beta`` / ``b``
    - ``-1`` for ``rc`` / ``c``
    - ``0`` for no suffix (release)
    - ``1`` for ``post``

    and suffix_number is the numeric part after the suffix (e.g.,
    ``rc2`` → 2, ``dev1`` → 1).  Defaults to ``0`` when absent.
    """
    segment = segment.strip().lower()
    suffix_map = {
        "dev": -4,
        "alpha": -3,
        "a": -3,
        "beta": -2,
        "b": -2,
        "rc": -1,
        "c": -1,
        "post": 1,
    }

    m = re.match(r"^(\d+)(.*)", segment)
    if m:
        num = int(m.group(1))
        suffix = m.group(2).strip()
        if not suffix:
            return (num, 0, 0)
        for key, order in suffix_map.items():
            if suffix.startswith(key):
                suffix_num_str = suffix[len(key) :]
                suffix_num = int(suffix_num_str) if suffix_num_str.isdigit() else 0
                return (num, order, suffix_num)
        return (num, 0, 0)

    # Pure prerelease segment without leading digits (e.g., "dev1", "rc2").
    # Use full-word prefixes only — single-letter aliases (a/b/c) are too
    # aggressive for standalone segments like "abc".
    _pure_prerelease_map = {
        "dev": -4,
        "alpha": -3,
        "beta": -2,
        "rc": -1,
        "post": 1,
    }
    for key, order in _pure_prerelease_map.items():
        if segment.startswith(key):
            suffix_num_str = segment[len(key) :]
            suffix_num = int(suffix_num_str) if suffix_num_str.isdigit() else 0
            return (0, order, suffix_num)

    # Non-numeric, non-prerelease segment — fail-open
    return (0, 0, 0)


def compare_versions(running: str, pinned: str) -> int:
    """Compare two version strings using PEP 440 semantics.

    Uses ``packaging.version.Version`` when available, falling back to
    :func:`_fallback_compare` on ``ImportError`` or parse error.

    Returns ``-1`` (running < pinned), ``0`` (equal), or ``1``
    (running > pinned).
    """
    try:
        from packaging.version import InvalidVersion, Version

        r = Version(running)
        p = Version(pinned)
        if r < p:
            return -1
        if r > p:
            return 1
        return 0
    except ImportError:
        print(
            "  ⚠  packaging library not available; falling back to segment-based version comparison",
            file=sys.stderr,
        )
        return _fallback_compare(running, pinned)
    except InvalidVersion:
        print(
            "  ⚠  Cannot parse version strings with PEP 440; falling back to segment-based comparison",
            file=sys.stderr,
        )
        return _fallback_compare(running, pinned)


def check_version_guard(git_root: Path | None, force_old_version: bool) -> str | None:
    """Check whether the running version satisfies the project pin.

    Args:
        git_root: Repository root path (``None`` when not in a repo).
        force_old_version: Whether ``--force-old-version`` was passed.

    Returns:
        ``None``  — proceed normally (version ok, no pin, or first-time setup).
        ``"block"`` — older version without force; caller should ``sys.exit(1)``.
        ``"force"`` — older version with force; caller should skip repo steps.
    """
    if git_root is None:
        return None

    from agentic_devtools.cli.config.project_config import load_project_config

    config = load_project_config(git_root=git_root)
    pinned = config.get("agdt_version")

    # FR-010: no agdt_version → first-time setup, proceed normally
    if pinned is None:
        return None

    pinned_str = str(pinned).strip()
    if not pinned_str:
        print(
            "  ⚠  Malformed agdt_version (empty) in project.json — proceeding normally",
            file=sys.stderr,
        )
        return None

    # FR-011: validate that pinned version is parseable
    try:
        from packaging.version import InvalidVersion, Version

        Version(pinned_str)
    except ImportError:
        pass  # packaging unavailable — fallback comparison will handle it
    except InvalidVersion:
        print(
            f"  ⚠  Malformed agdt_version '{pinned_str}' in project.json — proceeding normally",
            file=sys.stderr,
        )
        return None

    from agentic_devtools import __version__ as running_version

    cmp = compare_versions(running_version, pinned_str)

    if cmp >= 0:
        # Equal or newer — proceed normally; --force-old-version is a no-op (US3/AS4)
        return None

    # Running version is older than pinned
    if force_old_version:
        # FR-009: warn that repo files will not be modified
        print(
            f"  ⚠  Your agentic-devtools version ({running_version}) is older than the "
            f"project requires ({pinned_str}).\n"
            "     Running with --force-old-version: local environment will be configured,\n"
            "     but repo files will NOT be modified. This mode is not recommended.",
            file=sys.stderr,
        )
        return "force"

    # FR-005: block with actionable error message
    print(
        f"  ❌ Your agentic-devtools version ({running_version}) is older than the "
        f"project requires ({pinned_str}).\n"
        "     Please run `python setup-dev-tools.py` to upgrade, or use\n"
        "     --force-old-version to continue without repo changes.",
        file=sys.stderr,
    )
    return "block"
