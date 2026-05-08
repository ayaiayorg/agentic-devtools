"""Legacy migration for existing ``setup-dev-tools.py``.

Detects whether the current ``setup-dev-tools.py`` is a legacy
monolithic script (no ``# AGDT-MANAGED-ORCHESTRATOR`` marker) and
migrates its content to ``setup-repo-specific-dev-tools.py``.
"""

from __future__ import annotations

from pathlib import Path

from .atomic_write import atomic_write
from .constants import ORCHESTRATOR_MARKER

_MIGRATION_SEPARATOR = (
    "\n\n"
    "# ── Migrated from legacy setup-dev-tools.py ──────────────────────\n"
    "# The content below was automatically moved here by agdt-setup.\n"
    "# Review and adjust as needed.\n"
    "# ─────────────────────────────────────────────────────────────────\n"
)


def detect_legacy_script(setup_dev_tools_path: Path) -> bool:
    """Return ``True`` if *setup_dev_tools_path* is a legacy monolithic script.

    A file is considered "legacy" when it exists and does **not** contain
    the ``# AGDT-MANAGED-ORCHESTRATOR`` marker.
    """
    if not setup_dev_tools_path.is_file():
        return False
    try:
        content = setup_dev_tools_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        # Unreadable file — treat as legacy to prevent accidental overwrite.
        return True
    return ORCHESTRATOR_MARKER not in content


def migrate_legacy_content(
    legacy_path: Path,
    repo_specific_path: Path,
) -> tuple[bool, str]:
    """Move legacy script content into *repo_specific_path*.

    * If *repo_specific_path* does **not** exist, the content is written
      verbatim.
    * If *repo_specific_path* **already** exists, the legacy content is
      appended below a separator comment.

    Returns a ``(success, message)`` tuple where *success* is ``True``
    when migration completed without errors.
    """
    try:
        legacy_content = legacy_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return False, f"  ⚠ Failed to read legacy script: {exc}"

    if not legacy_content.strip():
        return True, "  ℹ Legacy setup-dev-tools.py is empty — skipping migration."

    try:
        if repo_specific_path.is_file():
            try:
                existing = repo_specific_path.read_text(encoding="utf-8")
            except UnicodeDecodeError as exc:
                return False, f"  ⚠ Failed to read {repo_specific_path.name}: {exc}"
            combined = existing.rstrip() + _MIGRATION_SEPARATOR + legacy_content
            atomic_write(repo_specific_path, combined)
            return True, f"  ✓ Legacy content appended to {repo_specific_path.name} (below migration separator)."
        else:
            atomic_write(repo_specific_path, legacy_content)
            return True, f"  ✓ Legacy content moved to {repo_specific_path.name}."
    except OSError as exc:
        return False, f"  ⚠ Failed to migrate legacy content: {exc}"
