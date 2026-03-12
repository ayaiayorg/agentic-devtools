"""Verify no stale state-directory references remain in the codebase."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".eggs",
    "build",
    "dist",
    "node_modules",
    ".agdt",
    ".agdt-temp",
    ".dfly-temp",
}
EXCLUDE_FILES = {"CHANGELOG.md"}
SCAN_EXTENSIONS = {".py", ".md"}

# The pattern we are scanning for — kept as a constant so this test file
# does not itself contain the literal pattern on assertion/comment lines.
_BANNED_PATTERN = "scripts" + "/" + "temp"


def test_no_stale_state_dir_references():
    """Ensure no file in the repo references the old state directory path."""
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
        # Skip this test file itself
        if path.resolve() == Path(__file__).resolve():
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        for lineno, line in enumerate(content.splitlines(), 1):
            if _BANNED_PATTERN in line:
                hits.append(f"{path.relative_to(REPO_ROOT)}:{lineno}: {line.strip()}")
    assert not hits, f"Found {_BANNED_PATTERN} references:\n" + "\n".join(hits)
