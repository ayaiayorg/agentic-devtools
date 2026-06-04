"""
Utility functions for PR review workflow.

Most functions are pure with no side effects (no state reading, no API calls, no file I/O).

Exceptions:
- ``build_full_file_content_section`` reads files from disk to embed full file content in prompts.
- ``resolve_repository_root`` may invoke ``git`` as a subprocess to discover
    the repository root when no explicit ``repo_root`` is provided.
"""

import hashlib
import re
import stat
import subprocess
from pathlib import Path

# Regex to extract Jira issue keys from PR titles
# Matches patterns like: PROJECT-1234, [PROJECT-1234], (PROJECT-1234), feature(PROJECT-1234):
JIRA_ISSUE_KEY_PATTERN = re.compile(r"\b([A-Z]+-\d+)\b")


def extract_jira_issue_key_from_title(title: str) -> str | None:
    """
    Extract Jira issue key from a PR title.

    Looks for patterns like:
    - feature(PROJECT-1234): description
    - [PROJECT-1234] description
    - fix(PROJECT-1234 / PROJECT-5678): description (returns first match)

    Args:
        title: Pull request title

    Returns:
        First Jira issue key found, or None
    """
    if not title:
        return None

    matches = JIRA_ISSUE_KEY_PATTERN.findall(title)
    return matches[0] if matches else None


def convert_to_prompt_filename(file_path: str) -> str:
    """
    Convert file path to a unique prompt filename using SHA256 hash.

    Args:
        file_path: Repository file path

    Returns:
        Filename like "file-abc123def456.md"
    """
    if not file_path:
        return "file-metadata-missing.md"

    hash_obj = hashlib.sha256(file_path.encode("utf-8"))
    hash_str = hash_obj.hexdigest()[:16].lower()
    return f"file-{hash_str}.md"


def normalize_repo_path(path: str) -> str | None:
    """
    Normalize a repository path to /path/to/file format.

    Args:
        path: File path (may have backslashes, leading slashes, etc.)

    Returns:
        Normalized path like "/src/app/file.ts" or None if invalid
    """
    if not path or not path.strip():
        return None

    clean = path.strip().replace("\\", "/").strip()
    without_leading = clean.lstrip("/")
    if not without_leading:  # pragma: no cover
        return None
    return f"/{without_leading}"


def get_root_folder(file_path: str) -> str:
    """
    Get the root folder from a file path.

    Args:
        file_path: Repository file path

    Returns:
        Root folder name (e.g., "src") or "root" if no folder
    """
    if not file_path:
        return "root"

    normalized = file_path.replace("\\", "/")
    if "/" not in normalized:
        return "root"
    return normalized.split("/")[0]


def filter_threads(threads: list[dict]) -> list[dict]:
    """
    Filter out deleted threads and comments.

    Args:
        threads: List of PR thread dictionaries

    Returns:
        Filtered list with deleted items removed
    """
    if not threads:
        return []

    filtered = []
    for thread in threads:
        if not thread:
            continue
        if thread.get("isDeleted"):
            continue

        comments = thread.get("comments", [])
        filtered_comments = [c for c in comments if c and not c.get("isDeleted")]

        if not filtered_comments:
            continue

        # Create a copy to avoid mutating the original
        thread_copy = dict(thread)
        thread_copy["comments"] = filtered_comments
        filtered.append(thread_copy)

    return filtered


def get_threads_for_file(threads: list[dict], file_path: str) -> list[dict]:
    """
    Get threads that are associated with a specific file.

    Args:
        threads: List of PR thread dictionaries
        file_path: Repository file path to match

    Returns:
        List of threads for the specified file
    """
    if not threads:
        return []

    normalized_path = file_path.replace("\\", "/").lstrip("/")
    matching = []

    for thread in threads:
        if not thread:
            continue

        context = thread.get("threadContext")
        thread_path = None

        if context:
            if context.get("filePath"):
                thread_path = context["filePath"]
            elif context.get("leftFileStart", {}).get("filePath"):
                thread_path = context["leftFileStart"]["filePath"]
            elif context.get("rightFileStart", {}).get("filePath"):
                thread_path = context["rightFileStart"]["filePath"]

        if not thread_path:
            continue

        thread_path = thread_path.replace("\\", "/").lstrip("/")
        if thread_path == normalized_path:
            matching.append(thread)

    return matching


def build_reviewed_paths_set(pr_details: dict) -> set:
    """
    Build a set of already-reviewed file paths from PR details.

    .. deprecated::
        This function is no longer called by the review workflow.
        The review-all-files approach now reviews every file each run and uses
        ``determine_processing_path()`` for inheritance decisions instead.
        Retained for backward compatibility.

    Args:
        pr_details: Full PR details payload

    Returns:
        Set of lowercase normalized paths that have been reviewed
    """
    # DEPRECATED — retained for backward compatibility
    reviewed_paths = set()
    reviewer_data = pr_details.get("reviewer", {}) or {}
    reviewed_files = reviewer_data.get("reviewedFiles", []) or []

    for path in reviewed_files:
        normalized = normalize_repo_path(path)
        if normalized:
            reviewed_paths.add(normalized.lower())

    return reviewed_paths


def resolve_repository_root(repo_root: Path | None = None) -> Path:
    """Return repository root when available, else fall back to current directory."""
    if repo_root is not None:
        return repo_root

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return Path(result.stdout.strip())
    except OSError:
        pass

    return Path.cwd()


def _select_markdown_fence(content: str) -> str:
    """Choose a backtick fence that cannot be closed by content."""
    longest_run = 0
    for match in re.finditer(r"`+", content):
        longest_run = max(longest_run, len(match.group(0)))

    return "`" * max(3, longest_run + 1)


# ---------------------------------------------------------------------------
# Full-file-content helpers for review prompts
# ---------------------------------------------------------------------------

BINARY_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".bmp",
        ".ico",
        ".svg",
        ".woff",
        ".woff2",
        ".ttf",
        ".eot",
        ".otf",
        ".pdf",
        ".zip",
        ".tar",
        ".gz",
        ".exe",
        ".dll",
        ".so",
        ".dylib",
        ".bin",
        ".dat",
        ".db",
        ".sqlite",
    }
)

MAX_FILE_CONTENT_SIZE: int = 51200  # 50 KB

_EXTENSION_LANGUAGE_MAP: dict[str, str] = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".js": "javascript",
    ".jsx": "jsx",
    ".json": "json",
    ".md": "markdown",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".xml": "xml",
    ".sh": "bash",
    ".bash": "bash",
    ".sql": "sql",
    ".rs": "rust",
    ".go": "go",
    ".java": "java",
    ".cs": "csharp",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".c": "c",
    ".h": "cpp",
    ".hpp": "cpp",
    ".rb": "ruby",
    ".swift": "swift",
    ".kt": "kotlin",
    ".toml": "toml",
    ".ini": "ini",
    ".cfg": "ini",
    ".txt": "text",
    ".dockerfile": "dockerfile",
}


def get_language_from_extension(file_path: str) -> str:
    """
    Map a file extension to a markdown fenced-code-block language identifier.

    Args:
        file_path: File path or name (e.g., ``src/app.ts``)

    Returns:
        Language identifier (e.g., ``typescript``) or ``""`` for unknown extensions.
    """
    if not file_path:
        return ""
    ext = Path(file_path).suffix.lower()
    return _EXTENSION_LANGUAGE_MAP.get(ext, "")


def is_binary_file(file_path: str) -> bool:
    """
    Check whether a file is considered binary based on its extension.

    Args:
        file_path: File path or name

    Returns:
        ``True`` if the extension (case-insensitive) is in ``BINARY_EXTENSIONS``.
    """
    if not file_path:
        return False
    ext = Path(file_path).suffix.lower()
    return ext in BINARY_EXTENSIONS


def build_full_file_content_section(
    file_path: str,
    change_type: str,
    repo_root: Path | None = None,
) -> list[str]:
    """
    Build the ``## Full File Content`` markdown section for a review prompt.

    For added/modified files the full working-tree content is embedded in a
    fenced code block.  Deleted, binary, oversized, or unreadable files get a
    short explanatory note instead.

    Args:
        file_path: Repository-relative file path (may have leading ``/``).
        change_type: Change type string. Supports both long-form values
            (``add``, ``edit``, ``delete``, ``rename``) and git-status codes
            (``A``, ``M``, ``D``, ``R``).
        repo_root: Optional repository root directory. When ``None``, the
            repository root is resolved via ``resolve_repository_root()``, which
            first attempts to discover the git toplevel (and may invoke a ``git``
            subprocess) and falls back to ``Path.cwd()`` when no repository root
            can be detected.

    Returns:
        List of markdown lines to append to the prompt.
    """
    header = ["", "## Full File Content", ""]

    # Deleted file
    normalized_change_type = (change_type or "").strip().lower()
    if normalized_change_type in {"delete", "d"}:
        return [*header, "_This file was deleted in this change._"]

    # Binary file
    if is_binary_file(file_path):
        return [*header, "_Binary file — content not included._"]

    # Resolve on-disk path and block traversal outside repository root.
    normalized = file_path.lstrip("/") if file_path else ""
    repo_root_path = resolve_repository_root(repo_root).resolve()
    resolved = (repo_root_path / normalized).resolve()

    if resolved != repo_root_path and not resolved.is_relative_to(repo_root_path):
        return [*header, "_File path is outside repository root._"]

    try:
        file_stat = resolved.stat()
    except FileNotFoundError:
        return [*header, "_File not found on disk._"]
    except OSError:
        return [*header, "_File could not be read._"]

    if not stat.S_ISREG(file_stat.st_mode):
        return [*header, "_File not found on disk._"]

    size = file_stat.st_size

    if size > MAX_FILE_CONTENT_SIZE:
        return [
            *header,
            f"_File too large ({size} bytes) — content not included. Threshold: {MAX_FILE_CONTENT_SIZE} bytes._",
        ]

    # Read content
    try:
        content = resolved.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return [*header, "_File could not be read._"]

    lang = get_language_from_extension(file_path)
    fence = _select_markdown_fence(content)
    return [*header, f"{fence}{lang}", content, fence]


def get_agdt_threads(threads: list[dict | None]) -> list[dict]:
    """Return only threads whose first comment contains an agdt-review marker.

    Convenience wrapper around :func:`~agentic_devtools.cli.azure_devops.marker.filter_agdt_threads`.

    Args:
        threads: List of Azure DevOps thread dicts.

    Returns:
        Filtered list of threads with an agdt-review marker.
    """
    from .marker import filter_agdt_threads

    return filter_agdt_threads(threads)
