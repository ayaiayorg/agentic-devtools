"""Legacy migration for existing ``setup-dev-tools.py``.

Detects whether the current ``setup-dev-tools.py`` is a legacy
monolithic script (no ``# AGDT-MANAGED-ORCHESTRATOR`` marker) and
migrates its content to ``setup-repo-specific-dev-tools.py``.
"""

from __future__ import annotations

from pathlib import Path

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
    except OSError:
        return False
    return ORCHESTRATOR_MARKER not in content


def migrate_legacy_content(
    legacy_path: Path,
    repo_specific_path: Path,
) -> str:
    """Move legacy script content into *repo_specific_path*.

    * If *repo_specific_path* does **not** exist, the content is written
      verbatim.
    * If *repo_specific_path* **already** exists, the legacy content is
      appended below a separator comment.

    Returns a human-readable status message.
    """
    try:
        legacy_content = legacy_path.read_text(encoding="utf-8")
    except OSError as exc:
        return f"  ⚠ Failed to read legacy script: {exc}"

    if not legacy_content.strip():
        return "  ℹ Legacy setup-dev-tools.py is empty — skipping migration."

    try:
        if repo_specific_path.is_file():
            existing = repo_specific_path.read_text(encoding="utf-8")
            combined = existing.rstrip() + _MIGRATION_SEPARATOR + legacy_content
            repo_specific_path.write_text(combined, encoding="utf-8")
            return f"  ✓ Legacy content appended to {repo_specific_path.name} (below migration separator)."
        else:
            repo_specific_path.write_text(legacy_content, encoding="utf-8")
            return f"  ✓ Legacy content moved to {repo_specific_path.name}."
    except OSError as exc:
        return f"  ⚠ Failed to migrate legacy content: {exc}"
