"""AI model attribution, commit hash URL builders, and status formatting for PR review comments.

Provides:
- format_status(): emoji-prefixed status for markdown, plain-text for CLI
- should_use_emoji(): auto-detect terminal emoji capability with env-var override
- build_commit_file_url(): file-level deep link in the PR file view
- build_commit_folder_url(): folder-level deep link (same URL pattern, folder path)
- build_commit_pr_url(): PR files tab link (no path parameter)
- get_model_icon(): model family icon from model name
- render_attribution_line(): full attribution line for embedding in review comments

KNOWN CONSTRAINT: Emoji rendering in terminals varies by OS, terminal emulator, and font.
The plain-text fallback ([APPROVED], [IN PROGRESS], etc.) is the safe default for all CLI
output. Emoji is only guaranteed safe in markdown content rendered by the Azure DevOps /
GitHub PR UI.
"""

import os
import sys
from typing import Optional

# Short commit hash display length (standard Git short hash)
SHORT_HASH_LENGTH = 7

# Generic AI icon used in all review comments
_GENERIC_AI_ICON = "🤖"

# Model family icon mapping: model name prefix (lowercase) → emoji icon
_MODEL_FAMILY_ICONS = {
    "claude": "🧠",
    "gpt": "🔮",
    "gemini": "💎",
}

# Status emoji/plain-text mapping: status value → (emoji label, plain-text label)
_STATUS_MAP = {
    "unreviewed": ("⏳ Unreviewed", "[UNREVIEWED]"),
    "in-progress": ("🔃 In Progress", "[IN PROGRESS]"),
    "approved": ("✅ Approved", "[APPROVED]"),
    "needs-work": ("📝 Needs Work", "[NEEDS WORK]"),
}


def format_status(status: str, use_emoji: bool = True) -> str:
    """Return status string with or without emoji prefix.

    For markdown/UI contexts (use_emoji=True), returns emoji-prefixed strings:
        "⏳ Unreviewed", "🔃 In Progress", "✅ Approved", "📝 Needs Work"

    For CLI/terminal output (use_emoji=False), returns plain-text fallback:
        "[UNREVIEWED]", "[IN PROGRESS]", "[APPROVED]", "[NEEDS WORK]"

    CLI fallback is the safe default because emoji rendering in terminals varies
    by OS, terminal emulator, and font. Emoji is only guaranteed safe in markdown
    rendered by the Azure DevOps / GitHub PR UI.

    Args:
        status: One of 'unreviewed', 'in-progress', 'approved', 'needs-work'.
                Unknown values are returned as-is (no prefix added).
        use_emoji: True for markdown/UI contexts, False for CLI/terminal output.

    Returns:
        Formatted status string, e.g. '✅ Approved' or '[APPROVED]'.
    """
    entry = _STATUS_MAP.get(status)
    if entry is None:
        return status
    return entry[0] if use_emoji else entry[1]


def should_use_emoji() -> bool:
    """Determine whether emoji output is safe for the current terminal.

    Checks (in priority order):
    1. ``AGDT_USE_EMOJI`` environment variable: "true" → True, "false" → False.
       Any other value is treated as unset and falls through to auto-detection.
    2. Auto-detection: stdout is a TTY AND the locale/encoding is UTF-8 capable.

    Returns:
        True if emoji output is safe, False for plain-text fallback.
    """
    env_val = os.environ.get("AGDT_USE_EMOJI", "").strip().lower()
    if env_val == "true":
        return True
    if env_val == "false":
        return False
    # Auto-detect: requires both a TTY and a UTF-8 capable locale
    if not sys.stdout.isatty():
        return False
    encoding = (getattr(sys.stdout, "encoding", None) or "").lower().replace("-", "")
    return encoding.startswith("utf")


def get_model_icon(model_name: Optional[str]) -> str:
    """Return the model family icon for a given model name.

    Matches by lowercase prefix against the known model family icon mapping:
        Claude → 🧠, GPT → 🔮, Gemini → 💎

    Falls back to the generic AI icon (🤖) for unknown or None model names.

    Args:
        model_name: Model identifier string (e.g. "Claude Opus 4.6"). May be None.

    Returns:
        A single emoji character representing the model family.
    """
    if not model_name:
        return _GENERIC_AI_ICON
    lower = model_name.lower()
    for prefix, icon in _MODEL_FAMILY_ICONS.items():
        if lower.startswith(prefix):
            return icon
    return _GENERIC_AI_ICON


def build_commit_file_url(
    organization: str,
    project: str,
    repo_name: str,
    pr_id: int,
    file_path: str,
    iteration: int,
    base: Optional[int] = None,
) -> str:
    """Build a URL to a specific file in the PR file view at a given iteration.

    Args:
        organization: Azure DevOps organization URL (trailing slash stripped).
        project: Project name.
        repo_name: Repository name.
        pr_id: Pull request ID.
        file_path: Repository file path. A leading '/' is added if missing.
        iteration: Iteration ID to view.
        base: Base iteration for diff comparison. Defaults to ``iteration - 1``.

    Returns:
        URL string pointing to the file at the specified iteration.
    """
    org = organization.rstrip("/")
    if not file_path.startswith("/"):
        file_path = "/" + file_path
    effective_base = iteration - 1 if base is None else base
    return (
        f"{org}/{project}/_git/{repo_name}/pullrequest/{pr_id}"
        f"?_a=files&base={effective_base}&iteration={iteration}&path={file_path}"
    )


def build_commit_folder_url(
    organization: str,
    project: str,
    repo_name: str,
    pr_id: int,
    folder_path: str,
    iteration: int,
    base: Optional[int] = None,
) -> str:
    """Build a URL to a folder view in the PR file tab at a given iteration.

    The URL follows the same pattern as the file URL but uses a folder path.
    Azure DevOps does not have a dedicated folder deep-link; the folder path
    is provided as the ``path`` parameter and serves as a visual context hint.

    Args:
        organization: Azure DevOps organization URL (trailing slash stripped).
        project: Project name.
        repo_name: Repository name.
        pr_id: Pull request ID.
        folder_path: Folder path. A leading '/' is added if missing.
        iteration: Iteration ID to view.
        base: Base iteration for diff comparison. Defaults to ``iteration - 1``.

    Returns:
        URL string pointing to the PR files tab filtered to the folder path.
    """
    org = organization.rstrip("/")
    if not folder_path.startswith("/"):
        folder_path = "/" + folder_path
    effective_base = iteration - 1 if base is None else base
    return (
        f"{org}/{project}/_git/{repo_name}/pullrequest/{pr_id}"
        f"?_a=files&base={effective_base}&iteration={iteration}&path={folder_path}"
    )


def build_commit_pr_url(
    organization: str,
    project: str,
    repo_name: str,
    pr_id: int,
    iteration: int,
    base: Optional[int] = None,
) -> str:
    """Build a URL to the PR files tab at a given iteration (no file/folder filter).

    Args:
        organization: Azure DevOps organization URL (trailing slash stripped).
        project: Project name.
        repo_name: Repository name.
        pr_id: Pull request ID.
        iteration: Iteration ID to view.
        base: Base iteration for diff comparison. Defaults to ``iteration - 1``.

    Returns:
        URL string pointing to the PR files tab at the specified iteration.
    """
    org = organization.rstrip("/")
    effective_base = iteration - 1 if base is None else base
    return f"{org}/{project}/_git/{repo_name}/pullrequest/{pr_id}?_a=files&base={effective_base}&iteration={iteration}"


def render_attribution_line(
    model_name: Optional[str],
    commit_hash: Optional[str],
    commit_url: Optional[str],
    model_icon: Optional[str] = None,
) -> str:
    """Render the AI model attribution line for embedding in a review comment.

    Returns an empty string when either ``model_name`` or ``commit_hash`` is
    None or empty — partial attribution is not rendered.

    Format when all parameters are provided:
        🤖 *Reviewed by* 🧠 **{model_name}** *at commit:* [`{short_hash}`]({commit_url})

    where the model family icon (🧠) is derived from ``model_name`` via
    ``get_model_icon()`` unless ``model_icon`` is supplied explicitly.

    Args:
        model_name: Model identifier (e.g. "Claude Opus 4.6"). None → empty string.
        commit_hash: Commit hash (full or short). None → empty string.
        commit_url: URL linking to the reviewed code state. May be None when
                    commit_hash is also None; if commit_hash is provided but
                    commit_url is None the link falls back to bare hash text.
        model_icon: Override the auto-detected model family icon. If None,
                    the icon is looked up from ``get_model_icon(model_name)``.

    Returns:
        Rendered attribution markdown line, or empty string if incomplete.
    """
    if not model_name or not commit_hash:
        return ""
    family_icon = model_icon if model_icon is not None else get_model_icon(model_name)
    short_hash = commit_hash[:SHORT_HASH_LENGTH]
    if commit_url:
        commit_ref = f"[`{short_hash}`]({commit_url})"
    else:
        commit_ref = f"`{short_hash}`"
    return f"{_GENERIC_AI_ICON} *Reviewed by* {family_icon} **{model_name}** *at commit:* {commit_ref}"
