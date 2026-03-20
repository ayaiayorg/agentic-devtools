"""Mirrors bundled agent/prompt skill files into a target repository.

The injection places files directly into ``.github/agents/`` and
``.github/prompts/`` in the target repo (flat layout — no subdirectories),
with a managed ``agdt.README.md`` manifest in each.  Files from source
subdirectories are flattened by encoding the directory name into the
filename (e.g. ``sub/foo.agent.md`` → ``agdt.sub.foo.agent.md``).
"""

from __future__ import annotations

import re
import shutil
import warnings
from pathlib import Path
from typing import Dict, List, Optional

import yaml

_MANAGED_PREFIX = "agdt."
_MANAGED_README = _MANAGED_PREFIX + "README.md"
_SPECKIT_PREFIX = "speckit."
_ALPHA_ONLY_RE = re.compile(r"[^a-zA-Z]")

# ---------------------------------------------------------------------------
# Bundled-source resolution
# ---------------------------------------------------------------------------

_BUNDLED_DIR = Path(__file__).parent / "_bundled_skills"


def _get_source_dir(kind: str) -> Optional[Path]:
    """Return the directory that contains the bundled *kind* files.

    For wheel installs the files live under ``_bundled_skills/<kind>/``.
    For editable installs the ``force-include`` has not run, so we fall
    back to the repo-level ``.github/<kind>/`` directory.

    Returns ``None`` when neither location exists (corrupted install).
    """
    bundled = _BUNDLED_DIR / kind
    # Wheel install — has actual .md files (possibly in subdirs) besides __init__.py
    if bundled.is_dir() and any(bundled.rglob("*.md")):
        return bundled

    # Editable-install fallback: climb to the repo root
    repo_root = Path(__file__).resolve().parent.parent
    github_dir = repo_root / ".github" / kind
    if github_dir.is_dir():
        return github_dir

    # Corrupted / minimal install — return None
    return None


def _ensure_github_gitignore_unignores_agdt(git_root: Path) -> None:
    """Ensure `.github/.gitignore` does not ignore injected `.agdt` skills.

    Many repositories have a blanket `.agdt/` rule in their root `.gitignore`.
    That would also ignore `.github/agents/.agdt/` and `.github/prompts/.agdt/`,
    which prevents injected skills from being committed. To avoid mutating the
    root ignore file, we maintain a `.github/.gitignore` file with explicit
    un-ignore rules for these managed directories.

    .. note::

        This function is no longer called by :func:`inject_skills` after the
        migration from ``.agdt/`` subdirectories to a flat layout.  It is
        retained for backward compatibility in case external code references it.
    """

    github_dir = git_root / ".github"
    github_dir.mkdir(parents=True, exist_ok=True)
    github_gitignore = github_dir / ".gitignore"

    # Desired lines (order matters: comment followed by un-ignore rules).
    desired_lines = [
        "# Managed by agentic-devtools: ensure injected skills under .github are tracked.",
        "!agents/.agdt/",
        "!agents/.agdt/**",
        "!prompts/.agdt/",
        "!prompts/.agdt/**",
    ]

    existing_lines: List[str] = []
    if github_gitignore.exists():
        try:
            existing_lines = github_gitignore.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            warnings.warn(
                f"agentic-devtools: failed to read {github_gitignore!s}; "
                "injected skills under .github may remain ignored. "
                f"Underlying error: {exc}",
                RuntimeWarning,
            )
            # Injection should still proceed, even if skills remain ignored.
            return

    # Append any missing desired lines, preserving existing content.
    updated = False
    for line in desired_lines:
        if line not in existing_lines:
            existing_lines.append(line)
            updated = True

    if updated:
        try:
            github_gitignore.write_text(
                "\n".join(existing_lines) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            warnings.warn(
                f"agentic-devtools: failed to write {github_gitignore!s}; "
                "injected skills under .github may remain ignored. "
                f"Underlying error: {exc}",
                RuntimeWarning,
            )
            # Callers treat injection I/O errors as a best-effort operation.
            return


def _list_md_files(source_dir: Path, kind: str) -> List[Path]:
    """Return the ``.md`` files that should be injected for *kind*.

    Uses ``rglob`` so that future subdirectory structures are preserved.

    * ``agents`` → all non-hidden ``*.md`` files (excluding hidden files/dirs).
    * ``prompts`` → only ``*.prompt.md`` files (excluding hidden files/dirs).
    """
    if kind == "agents":
        return sorted(
            p
            for p in source_dir.rglob("*.md")
            if p.is_file() and not any(part.startswith(".") for part in p.relative_to(source_dir).parts)
        )
    # prompts
    return sorted(
        p
        for p in source_dir.rglob("*.prompt.md")
        if p.is_file() and not any(part.startswith(".") for part in p.relative_to(source_dir).parts)
    )


# ---------------------------------------------------------------------------
# YAML front-matter parsing
# ---------------------------------------------------------------------------


def _derive_fallback_description_from_markdown(content: str) -> Optional[str]:
    """Derive a short description from Markdown *content*.

    Prefers the first heading line (``#``-prefixed); otherwise uses the first
    non-empty line. Returns ``None`` when no suitable line is found.
    """
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip()
            if heading:
                return heading
        else:
            return stripped
    return None


def _parse_frontmatter(content: str) -> Dict[str, object]:
    """Extract YAML front-matter from *content*.

    Returns a dictionary of parsed front-matter keys. When no valid
    front-matter block is found (missing, empty, malformed, or containing
    non-mapping YAML), the returned dict may still contain a derived
    ``_agdt_fallback_description`` entry based on the first Markdown
    heading or first non-empty line in the body. If no fallback
    description can be derived, an empty dict is returned.
    """
    if not content.startswith("---"):
        # No front-matter block; derive a fallback description from the whole
        # content so callers can still present something meaningful.
        fallback = _derive_fallback_description_from_markdown(content)
        return {"_agdt_fallback_description": fallback} if fallback else {}

    # Use splitlines() so that both LF and CRLF line endings are handled
    # identically — content.find("\n---") would miss "\r\n---" on Windows.
    lines = content.splitlines()
    close_idx = next(
        (i for i, line in enumerate(lines) if i > 0 and line == "---"),
        None,
    )
    if close_idx is None:
        # Malformed front-matter; derive a fallback description from the body
        # after the opening delimiter (if any) so we do not return the leading
        # '---' line itself as the description.
        body_without_delimiter = "\n".join(lines[1:]) if len(lines) > 1 else ""
        source_for_fallback = body_without_delimiter or content
        fallback = _derive_fallback_description_from_markdown(source_for_fallback)
        return {"_agdt_fallback_description": fallback} if fallback else {}

    raw = "\n".join(lines[1:close_idx]).strip()
    body = "\n".join(lines[close_idx + 1 :])
    fallback = _derive_fallback_description_from_markdown(body) if body else None
    if not raw:
        return {"_agdt_fallback_description": fallback} if fallback else {}
    try:
        result = yaml.safe_load(raw)
        if not isinstance(result, dict):
            result = {}
    except yaml.YAMLError:
        result = {}
    if fallback and "_agdt_fallback_description" not in result:
        result["_agdt_fallback_description"] = fallback
    return result


def _extract_description(frontmatter: dict[str, object], kind: str) -> str:
    """Return a human-readable description from *frontmatter*.

    * For ``agents``: uses the ``description`` key.
    * For ``prompts``: uses the ``agent`` key.

    Falls back to a derived description from the Markdown body when available,
    otherwise to ``"—"``.
    """
    if kind == "agents":
        desc = frontmatter.get("description")
    else:
        desc = frontmatter.get("agent")
    if not desc:
        desc = frontmatter.get("_agdt_fallback_description")
    return str(desc) if desc else "\u2014"


# ---------------------------------------------------------------------------
# README generation
# ---------------------------------------------------------------------------


def _generate_readme(files: list[tuple[str, str]], kind: str) -> str:
    """Produce a managed ``agdt.README.md`` for the target directory.

    Args:
        files: list of ``(filename, description)`` tuples.
        kind: ``"agents"`` or ``"prompts"``.
    """
    label = "Agent" if kind == "agents" else "Prompt"
    lines = [
        f"# Managed {label} Skills",
        "",
        "> **This folder is managed by [agentic-devtools](https://github.com/ayaiayorg/agentic-devtools).**",
        "> Do **not** edit these files manually — they are overwritten by `agdt-setup`.",
        "",
        "The files below are mirrored from the `agentic-devtools` package so that",
        "Copilot CLI and similar tools can discover and use them by convention.",
        "They should be checked into source control like any other `.github`",
        "configuration, and any local edits will be overwritten the next time",
        "`agdt-setup` is run.",
        "",
        "## File Manifest",
        "",
        "| File | Description |",
        "| ---- | ----------- |",
    ]
    for filename, desc in files:
        lines.append(f"| `{filename}` | {desc} |")
    lines.extend(
        [
            "",
            "## Regeneration",
            "",
            "Run `agdt-setup` to update these files.  Stale files (removed in newer",
            "package versions) are automatically cleaned up.",
            "",
        ]
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Filename flattening
# ---------------------------------------------------------------------------


def _flatten_filename(rel_path: Path) -> str:
    """Compute the flat target filename for a source file.

    Root-level files keep their name unchanged.
    Files in subdirectories get the managed prefix (``_MANAGED_PREFIX``)
    followed by sanitized directory parts and the original filename.
    Only a-zA-Z characters are kept from directory names.
    """
    parts = rel_path.parts
    if len(parts) == 1:
        return parts[0]
    dir_parts = parts[:-1]
    sanitized = [_ALPHA_ONLY_RE.sub("", p) for p in dir_parts]
    sanitized = [s for s in sanitized if s]  # drop empty after sanitization
    if not sanitized:
        return parts[-1]
    return _MANAGED_PREFIX + ".".join(sanitized) + "." + parts[-1]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def inject_skills(git_root: Optional[Path]) -> bool:
    """Mirror bundled agent/prompt files into the target repo.

    Places files directly into ``{git_root}/.github/agents/`` and
    ``{git_root}/.github/prompts/`` (flat layout), copying all relevant
    ``.md`` files and generating a managed ``agdt.README.md`` manifest in
    each.  Files from source subdirectories are flattened by encoding the
    directory name into the filename.

    As a one-time migration, any old ``.agdt/`` subdirectories are removed.

    Args:
        git_root: Repository/worktree root.  When ``None`` (not in a git
            repo) no files are written and the function returns ``False``.

    Returns:
        ``True`` when both kinds (agents/prompts) were injected successfully.
        Returns ``False`` when:
        - ``git_root`` is ``None``,
        - a source directory for a required kind cannot be resolved,
        - a ``UnicodeDecodeError`` occurs while reading source files (non-UTF8
          content), or
        - an ``OSError`` occurs while writing mirrored files or manifests.
    """
    if git_root is None:
        return False

    try:
        overall_success = True
        for kind in ("agents", "prompts"):
            source_dir = _get_source_dir(kind)
            if source_dir is None:
                # Missing source for this kind (e.g. corrupted/minimal install) —
                # do not treat this as an empty snapshot, and do not delete or
                # overwrite any existing injected files. Mark overall result as
                # failure so callers can surface a warning.
                overall_success = False
                continue

            target_dir = git_root / ".github" / kind
            target_dir.mkdir(parents=True, exist_ok=True)

            # One-time migration: remove old .agdt/ subdirectory.
            # Guard against symlinks to avoid recursively deleting a
            # symlink target — just remove the link itself.
            old_agdt = target_dir / ".agdt"
            if old_agdt.is_symlink():
                old_agdt.unlink()
            elif old_agdt.is_dir():
                shutil.rmtree(old_agdt)

            # Determine which files to inject
            source_files = _list_md_files(source_dir, kind)
            # Exclude root-level ``agdt.README.md`` — the managed manifest
            # file generated by a previous run.  In editable-install scenarios
            # the repo's own ``.github/<kind>`` serves as source, so a leftover
            # manifest would otherwise be picked up as an injectable skill.
            # Only the *root-level* manifest is excluded; a nested file with the
            # same name (e.g. ``sub/agdt.README.md``) is legitimate and should
            # not be silently skipped.
            # Note: a plain ``README.md`` (without the managed prefix) is
            # already excluded by the ``p.name.startswith(_MANAGED_PREFIX)``
            # filter below, so no separate check is needed.
            source_files = [
                p
                for p in source_files
                if p.relative_to(source_dir) != Path(_MANAGED_README)
            ]
            # Exclude speckit.* files — they reference .specify/ scripts not
            # available in target repos and are non-functional without the
            # full speckit scaffold.
            source_files = [p for p in source_files if not p.name.startswith(_SPECKIT_PREFIX)]
            # Only inject files whose *source* filename starts with the
            # managed prefix (``agdt.``).  Root-level files without the prefix
            # (e.g. ``copilot-instructions.md``) are repo-specific and must
            # not be copied into target repos where they could overwrite
            # user-authored files.  This also keeps the injected file set
            # aligned with stale cleanup, which only removes ``agdt.*`` files.
            source_files = [p for p in source_files if p.name.startswith(_MANAGED_PREFIX)]

            # Build set of flattened filenames for stale-cleanup comparison.
            # Also detect duplicate flat names — would cause silent overwriting.
            # The check uses ``casefold()`` so collisions on case-insensitive
            # filesystems (Windows, macOS default) are caught too.
            source_rel_names: set[str] = set()
            flat_name_origins: dict[str, Path] = {}
            _seen_ci: dict[str, str] = {}  # casefold → first flat_name
            for src in source_files:
                flat_name = _flatten_filename(src.relative_to(source_dir))
                key = flat_name.casefold()
                prev_flat = _seen_ci.get(key)
                if prev_flat is not None and prev_flat != flat_name:
                    # Case-insensitive collision (different casing)
                    warnings.warn(
                        f"agentic-devtools: duplicate flat filename {flat_name!r} "
                        f"(case-insensitive match of {prev_flat!r}) "
                        f"from {src!s} (first seen from {flat_name_origins[prev_flat]!s}); "
                        "only the last source will be injected on "
                        "case-insensitive filesystems.",
                        RuntimeWarning,
                    )
                elif flat_name in flat_name_origins:
                    # Exact duplicate
                    warnings.warn(
                        f"agentic-devtools: duplicate flat filename {flat_name!r} "
                        f"from {src!s} (first seen from {flat_name_origins[flat_name]!s}); "
                        "only the last source will be injected.",
                        RuntimeWarning,
                    )
                # Remove old casing entry if it differs, so the latest wins
                if prev_flat is not None and prev_flat != flat_name:
                    flat_name_origins.pop(prev_flat, None)
                    source_rel_names.discard(prev_flat)
                _seen_ci[key] = flat_name
                flat_name_origins[flat_name] = src
                source_rel_names.add(flat_name)

            # Copy files, flattening subdirectory structure into filenames.
            # Iterate the de-duplicated mapping so each flat_name is written
            # exactly once (the last source wins, consistent with the warning).
            manifest: list[tuple[str, str]] = []
            for flat_name, src in flat_name_origins.items():
                dest = target_dir / flat_name
                # Guard against SameFileError when source and target resolve
                # to the same file — happens for editable installs targeting
                # this repo's own .github/<kind> directory.
                if src.resolve() != dest.resolve():
                    shutil.copy2(src, dest)
                try:
                    content = src.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    # Keep processing remaining files, but surface non-UTF8
                    # source content as an overall injection failure. Still
                    # include the file in the manifest with a fallback
                    # description so the managed README stays accurate.
                    overall_success = False
                    desc = "Non-UTF-8 source; description unavailable."
                else:
                    fm = _parse_frontmatter(content)
                    desc = _extract_description(fm, kind)
                manifest.append((flat_name, desc))

            # Remove stale agdt.* files not in current source set
            for existing in target_dir.iterdir():
                if (
                    existing.is_file()
                    and existing.name.startswith(_MANAGED_PREFIX)
                    and existing.name != _MANAGED_README
                    and existing.name not in source_rel_names
                ):
                    existing.unlink()

            # Generate agdt.README.md
            readme_path = target_dir / _MANAGED_README
            readme_path.write_text(
                _generate_readme(manifest, kind),
                encoding="utf-8",
            )

        return overall_success
    except OSError:
        return False
