"""
Mirrors bundled agent/prompt skill files into a target repository so that
Copilot CLI and similar tools can discover them by convention.

The injection creates ``.github/agents/.agdt/`` and
``.github/prompts/.agdt/`` directories in the target repo, each containing
a managed ``README.md`` manifest.
"""

from __future__ import annotations

import shutil
import warnings
from pathlib import Path
from typing import Dict, List, Optional

import yaml

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
    """Produce a managed ``README.md`` for a ``.agdt/`` directory.

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
# Public API
# ---------------------------------------------------------------------------


def inject_skills(git_root: Optional[Path]) -> bool:
    """Mirror bundled agent/prompt files into the target repo.

    Creates ``{git_root}/.github/agents/.agdt/`` and
    ``{git_root}/.github/prompts/.agdt/``, copying all relevant ``.md``
    files and generating a managed ``README.md`` manifest in each.

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
        - an ``OSError`` occurs while writing mirrored files or manifests
          (excluding best-effort updates to ``.github/.gitignore``).
    """
    if git_root is None:
        return False

    try:
        overall_success = True
        _ensure_github_gitignore_unignores_agdt(git_root)
        for kind in ("agents", "prompts"):
            source_dir = _get_source_dir(kind)
            if source_dir is None:
                # Missing source for this kind (e.g. corrupted/minimal install) —
                # do not treat this as an empty snapshot, and do not delete or
                # overwrite any existing injected files. Mark overall result as
                # failure so callers can surface a warning.
                overall_success = False
                continue

            target_dir = git_root / ".github" / kind / ".agdt"
            target_dir.mkdir(parents=True, exist_ok=True)

            # Determine which files to inject
            source_files = _list_md_files(source_dir, kind)
            # Reserve the root-level README.md for the managed manifest in the
            # target .agdt/ directory by excluding only a source file whose
            # *relative* path is exactly "README.md". This prevents conflicts
            # where a root README.md would be copied and then immediately
            # overwritten by the generated manifest while still being listed in
            # the manifest, while still allowing nested READMEs (e.g.
            # "foo/README.md") to be mirrored as normal skill docs.
            source_files = [
                p
                for p in source_files
                if p.relative_to(source_dir) != Path("README.md")
            ]

            # Build set of relative paths for stale-cleanup comparison.
            source_rel_paths = {p.relative_to(source_dir) for p in source_files}

            # Copy files, preserving relative directory structure
            manifest: list[tuple[str, str]] = []
            for src in source_files:
                rel = src.relative_to(source_dir)
                dest = target_dir / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
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
                manifest.append((rel.as_posix(), desc))

            # Remove stale .md files (not in source), but keep the root README.md
            for existing in (p for p in target_dir.rglob("*.md") if p.is_file()):
                rel = existing.relative_to(target_dir)
                # Preserve only the managed root README.md; treat nested READMEs as normal files
                if rel == Path("README.md"):
                    continue
                if rel not in source_rel_paths:
                    existing.unlink()

            # Generate README.md
            readme_path = target_dir / "README.md"
            readme_path.write_text(
                _generate_readme(manifest, kind),
                encoding="utf-8",
            )

        return overall_success
    except OSError:
        return False
