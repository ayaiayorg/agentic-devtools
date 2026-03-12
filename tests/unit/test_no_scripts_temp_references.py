"""Verify no scripts/temp references remain in the codebase."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXCLUDE_DIRS = {".git", ".venv", "venv", "__pycache__", ".eggs", "build", "dist", "node_modules"}
EXCLUDE_FILES = {"CHANGELOG.md"}
SCAN_EXTENSIONS = {".py", ".md"}


def test_no_scripts_temp_references():
    """Ensure no file in the repo references the old scripts/temp/ path."""
    hits = []
    for path in REPO_ROOT.rglob("*"):
        if any(part in EXCLUDE_DIRS for part in path.parts):
            continue
        if path.name in EXCLUDE_FILES:
            continue
        if path.suffix not in SCAN_EXTENSIONS and path.name != ".gitignore":
            continue
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        for lineno, line in enumerate(content.splitlines(), 1):
            if "scripts/temp" in line:
                hits.append(f"{path.relative_to(REPO_ROOT)}:{lineno}: {line.strip()}")
    assert not hits, "Found scripts/temp references:\n" + "\n".join(hits)
