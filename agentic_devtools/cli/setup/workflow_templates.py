"""Workflow template generation for ``agdt-setup``.

Provides two public functions:

* :func:`list_available_templates` — metadata about bundled templates.
* :func:`generate_default_templates` — copy templates to a user directory.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Template metadata
# ---------------------------------------------------------------------------

_TEMPLATES_DIR = Path(__file__).parent / "templates"


@dataclass(frozen=True)
class TemplateInfo:
    """Immutable metadata for a bundled workflow template."""

    name: str
    filename: str
    description: str


_AVAILABLE_TEMPLATES: tuple[TemplateInfo, ...] = (
    TemplateInfo(
        name="Work on Issue",
        filename="work-on-issue.py",
        description="Starter workflow graph for working on an issue, based on the pilot workflow pattern.",
    ),
    TemplateInfo(
        name="Review PR",
        filename="review-pr.py",
        description="Skeleton workflow graph for reviewing a pull request.",
    ),
    TemplateInfo(
        name="README",
        filename="README.md",
        description="Documentation explaining how to customize workflow templates.",
    ),
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def list_available_templates() -> list[TemplateInfo]:
    """Return metadata for all bundled workflow templates."""
    return list(_AVAILABLE_TEMPLATES)


def generate_default_templates(target_dir: Path, overwrite: bool = False) -> list[Path]:
    """Copy bundled templates into *target_dir*.

    Creates *target_dir* (and parents) when it does not exist.  Files that
    already exist are skipped unless *overwrite* is ``True``.

    Returns:
        List of :class:`~pathlib.Path` objects for files actually written.
    """
    target_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for template in _AVAILABLE_TEMPLATES:
        source = _TEMPLATES_DIR / template.filename
        destination = target_dir / template.filename
        if destination.exists() and not overwrite:
            logger.debug("Skipping %s: already exists", template.filename)
            continue
        content = source.read_text(encoding="utf-8")
        destination.write_text(content, encoding="utf-8")
        logger.info("Generated template: %s", template.filename)
        written.append(destination)

    return written
