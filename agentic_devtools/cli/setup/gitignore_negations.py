"""Root ``.gitignore`` negation rules for ``.agdt/config/project.json``.

Ensures that ``project.json`` is tracked by Git even though the root
``.gitignore`` ignores ``.agdt/`` entirely.  The required negation
rules are inserted immediately after the ``.agdt/`` ignore line so
that Git's sequential rule evaluation un-ignores the config subtree.
"""

from __future__ import annotations

import sys
from pathlib import Path

_NEGATION_LINES = [
    "!.agdt/config/",
    "!.agdt/config/project.json",
]


def _detect_newline(content: str) -> str:
    """Return the dominant line ending in *content* (``\\r\\n`` or ``\\n``)."""
    if "\r\n" in content:
        return "\r\n"
    return "\n"


def ensure_root_gitignore_negations(git_root: Path) -> bool:
    """Insert negation rules into the root ``.gitignore`` if needed.

    Finds the ``.agdt/`` ignore line and appends the negation rules
    immediately after it.  Idempotent — only negation rules that appear
    *after* the ``.agdt/`` line are considered present, since earlier
    ones are overridden by Git's sequential rule evaluation.

    Returns ``True`` if the file was modified, ``False`` otherwise.
    """
    gitignore_path = git_root / ".gitignore"

    if not gitignore_path.exists():
        return False

    try:
        with open(gitignore_path, encoding="utf-8", newline="") as fh:
            content = fh.read()
    except (OSError, UnicodeDecodeError):
        print(
            f"  ⚠  Cannot read {gitignore_path} — skipping gitignore negation rules",
            file=sys.stderr,
        )
        return False

    lines = content.splitlines(keepends=True)

    newline = _detect_newline(content)

    # Find the .agdt/ ignore line (also matches .agdt/* from gitignore_updater)
    agdt_line_idx = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped in (".agdt/", ".agdt", ".agdt/*"):
            agdt_line_idx = i
            break

    if agdt_line_idx is None:
        # No .agdt/ rule found — negation rules are not needed
        return False

    # Only count negation lines as "present" when they appear *after*
    # the .agdt/ rule.  Negation lines that appear earlier are overridden
    # by the later .agdt/ ignore and are therefore ineffective.
    existing_after_agdt = {line.strip() for line in lines[agdt_line_idx + 1 :]}
    missing = [rule for rule in _NEGATION_LINES if rule not in existing_after_agdt]

    if not missing:
        # Both rules exist after ``.agdt/`` — verify the directory negation
        # appears before the file negation.  Git evaluates ``.gitignore``
        # rules sequentially, so ``!.agdt/config/project.json`` has no
        # effect if ``!.agdt/config/`` hasn't un-ignored the parent first.
        dir_neg_idx = None
        file_neg_idx = None
        for i, line in enumerate(lines):
            if i <= agdt_line_idx:
                continue
            stripped = line.strip()
            if stripped == _NEGATION_LINES[0] and dir_neg_idx is None:
                dir_neg_idx = i
            elif stripped == _NEGATION_LINES[1] and file_neg_idx is None:
                file_neg_idx = i

        if (
            dir_neg_idx is not None
            and file_neg_idx is not None
            and dir_neg_idx < file_neg_idx
        ):
            return False  # Both present and correctly ordered

        # Out-of-order: remove the misplaced file negation and re-insert
        # it in the correct position (handled by the insertion logic below).
        # ``file_neg_idx`` is guaranteed to be set here because ``not missing``
        # means both negation lines exist in ``existing_after_agdt`` and the
        # for-loop above always finds them.
        if file_neg_idx is not None:  # pragma: no branch – guaranteed by ``not missing``
            del lines[file_neg_idx]
        missing = [_NEGATION_LINES[1]]

    # Determine insertion point.  When the directory negation
    # ``!.agdt/config/`` already exists (only the file rule is missing),
    # insert the file negation *after* that directory line so the
    # gitignore ordering stays correct (parent un-ignore before child).
    # However, only use this special-case when the existing directory
    # negation appears *after* the ``.agdt/`` ignore rule — otherwise
    # the negation would be ineffective (the later ``.agdt/`` rule wins).
    insert_pos = agdt_line_idx + 1
    if "!.agdt/config/" in existing_after_agdt and missing == ["!.agdt/config/project.json"]:
        # The directory negation exists after the ``.agdt/`` rule.
        # Insert the file negation right after it so gitignore ordering
        # stays correct (parent un-ignore before child).
        dir_line_idx = next(
            i
            for i, line in enumerate(lines)
            if i > agdt_line_idx and line.strip() == "!.agdt/config/"
        )
        insert_pos = dir_line_idx + 1

    # Ensure the line before the insertion ends with a newline
    prev_line_idx = insert_pos - 1
    if prev_line_idx >= 0 and not lines[prev_line_idx].endswith("\n"):
        lines[prev_line_idx] += newline

    for i, rule in enumerate(missing):
        lines.insert(insert_pos + i, rule + newline)

    try:
        with open(gitignore_path, "w", encoding="utf-8", newline="") as fh:
            fh.write("".join(lines))
    except OSError:
        print(
            f"  ⚠  Cannot write to {gitignore_path} — skipping gitignore negation rules",
            file=sys.stderr,
        )
        return False

    return True
