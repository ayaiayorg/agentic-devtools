"""Suggestion verification for PR review re-scaffolding.

Before involving an AI reviewer on a new commit, this module checks whether
previous suggestions were addressed.  Each previous suggestion is categorised
as either **"unaddressed"** or **"needs_review"** based on whether its thread
has any replies and whether the file was changed in the new commit.

If ANY suggestion is unaddressed the review is aborted.  If all are
"needs_review" the AI reviewer is expected to evaluate them first.

All categorisation logic is pure — no API calls are made inside
``verify_previous_suggestions``.  Thread data must be pre-fetched and passed
in.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .review_state import SuggestionEntry

# Verification category constants
CATEGORY_UNADDRESSED = "unaddressed"
CATEGORY_NEEDS_REVIEW = "needs_review"


@dataclass
class SuggestionVerificationResult:
    """Categorisation result for a single previous suggestion."""

    suggestion: SuggestionEntry
    file_path: str
    category: str  # "unaddressed" or "needs_review"
    has_reply: bool
    file_changed: bool
    thread_status: str  # "active", "closed", etc.


def _thread_has_reply(thread_data: Dict[str, Any]) -> bool:
    """Return True if the thread has at least one reply beyond the original comment.

    Azure DevOps thread responses have a "comments" list; the first comment
    is the original post, so comment count > 1 indicates a reply.
    """
    comments = thread_data.get("comments", [])
    return len(comments) > 1


def _get_thread_status(thread_data: Dict[str, Any]) -> str:
    """Return the thread status string (e.g. "active", "closed", "fixed")."""
    return thread_data.get("status", "unknown")


def verify_previous_suggestions(
    previous_suggestions: List[SuggestionEntry],
    file_path: str,
    file_changed: bool,
    threads_data: Dict[int, Dict[str, Any]],
) -> List[SuggestionVerificationResult]:
    """Categorise each previous suggestion as "unaddressed" or "needs_review".

    Logic per suggestion:
    * Retrieve the thread from *threads_data* using ``suggestion.threadId``.
    * Check whether the thread has any replies beyond the original comment
      (comment count > 1).
    * **Unaddressed**: ``not has_reply and not file_changed``.
    * **Needs Review**: ``has_reply or file_changed`` (either condition is
      sufficient).

    Edge cases:
    * Thread not found in *threads_data* → categorised as "needs_review"
      (unknown state — let AI evaluate).

    The function is pure (no API calls).

    Args:
        previous_suggestions: List of suggestions from a file's
            ``previousSuggestions`` field.
        file_path: Repository file path the suggestions belong to.
        file_changed: Whether the file was changed in the new commit.
        threads_data: Pre-fetched mapping of ``{thread_id: thread_api_response}``.

    Returns:
        One ``SuggestionVerificationResult`` per input suggestion.
    """
    results: List[SuggestionVerificationResult] = []
    for suggestion in previous_suggestions:
        thread = threads_data.get(suggestion.threadId)
        if thread is None:
            # Thread deleted / not found — treat as needs_review
            results.append(
                SuggestionVerificationResult(
                    suggestion=suggestion,
                    file_path=file_path,
                    category=CATEGORY_NEEDS_REVIEW,
                    has_reply=False,
                    file_changed=file_changed,
                    thread_status="unknown",
                )
            )
            continue

        has_reply = _thread_has_reply(thread)
        thread_status = _get_thread_status(thread)

        if has_reply or file_changed:
            category = CATEGORY_NEEDS_REVIEW
        else:
            category = CATEGORY_UNADDRESSED

        results.append(
            SuggestionVerificationResult(
                suggestion=suggestion,
                file_path=file_path,
                category=category,
                has_reply=has_reply,
                file_changed=file_changed,
                thread_status=thread_status,
            )
        )
    return results


def categorize_all_suggestions(
    files_with_previous: Dict[str, List[SuggestionEntry]],
    changed_files: frozenset,
    threads_data: Dict[int, Dict[str, Any]],
) -> List[SuggestionVerificationResult]:
    """Run verification across multiple files and return a flat list.

    Args:
        files_with_previous: ``{file_path: [SuggestionEntry, …]}`` from
            ``FileEntry.previousSuggestions``.
        changed_files: Set of file paths that were changed in the new commit
            (new + modified).
        threads_data: Pre-fetched ``{thread_id: thread_api_response}``.

    Returns:
        Flat list of all ``SuggestionVerificationResult`` across all files.
    """
    all_results: List[SuggestionVerificationResult] = []
    for file_path, suggestions in files_with_previous.items():
        file_changed = file_path in changed_files
        all_results.extend(verify_previous_suggestions(suggestions, file_path, file_changed, threads_data))
    return all_results


def has_unaddressed(results: List[SuggestionVerificationResult]) -> bool:
    """Return True if any result is categorised as unaddressed."""
    return any(r.category == CATEGORY_UNADDRESSED for r in results)


def partition_results(
    results: List[SuggestionVerificationResult],
) -> tuple:
    """Split results into (unaddressed, needs_review) lists.

    Returns:
        Tuple of (unaddressed_list, needs_review_list).
    """
    unaddressed = [r for r in results if r.category == CATEGORY_UNADDRESSED]
    needs_review = [r for r in results if r.category == CATEGORY_NEEDS_REVIEW]
    return unaddressed, needs_review


# ---------------------------------------------------------------------------
# Rendering helpers for the abort-gate PR summary comment
# ---------------------------------------------------------------------------


def _reason_text(result: SuggestionVerificationResult) -> str:
    """Build a human-readable reason for a needs_review suggestion."""
    if result.has_reply and result.file_changed:
        return "reply exists and file changed"
    if result.has_reply:
        return "reply exists"
    return "file changed"


def render_abort_summary(
    unaddressed: List[SuggestionVerificationResult],
    needs_review: List[SuggestionVerificationResult],
    short_hash: str,
    model_name: str = "AI Reviewer",
    model_icon: str = "🤖",
) -> str:
    """Render a structured PR summary comment for the abort gate.

    This comment is posted when review is blocked due to unaddressed
    suggestions.

    Args:
        unaddressed: List of unaddressed verification results.
        needs_review: List of needs-review verification results.
        short_hash: Short commit hash for the new commit.
        model_name: Display name of the AI model.
        model_icon: Emoji icon for the AI model.

    Returns:
        Markdown string for the PR summary comment.
    """
    lines = [
        "## Overall PR Review Summary\n",
        f"{model_icon} *Automated check by* **{model_name}** *at commit:* `{short_hash}`\n",
        "*Status:* ⛔ Review Blocked — Unaddressed Suggestions\n",
        "The following suggestions from the previous review have not been "
        "addressed. AI review cannot proceed until they are resolved.\n",
    ]

    lines.append(f"### ⚠️ Unaddressed ({len(unaddressed)})\n")
    for r in unaddressed:
        lines.append(f"- {r.file_path} — {r.suggestion.linkText}: No reply, no file changes.")
    lines.append("")

    lines.append(f"### 🔍 Needs Review ({len(needs_review)})\n")
    if needs_review:
        for r in needs_review:
            lines.append(f"- {r.file_path} — {r.suggestion.linkText}: {_reason_text(r)}")
    else:
        lines.append("*(none)*")
    lines.append("")

    lines.append(
        "*Address the unaddressed suggestions and push a new commit, "
        "or reply explaining why no changes are needed. "
        "Then trigger a new review.*"
    )
    return "\n".join(lines)


def render_unaddressed_thread_comment(short_hash: str) -> str:
    """Render a comment to be posted on an unaddressed suggestion thread.

    Args:
        short_hash: Short commit hash of the new commit.

    Returns:
        Markdown comment string.
    """
    return (
        "⚠️ **Unaddressed Suggestion**\n\n"
        f"This suggestion has not been addressed in the latest commit (`{short_hash}`). "
        "No reply was provided and no changes were made to the file.\n\n"
        "Please either:\n"
        "1. Make the suggested changes and push a new commit.\n"
        "2. Reply to this thread explaining why no changes are needed."
    )


def fetch_threads_lookup(
    requests_module: Any,
    headers: Dict[str, str],
    threads_url: str,
) -> Optional[Dict[int, Dict[str, Any]]]:
    """Fetch all PR threads and build a thread_id → thread_data lookup.

    Makes a single API call regardless of suggestion count.

    Args:
        requests_module: The requests module.
        headers: Auth headers.
        threads_url: The threads API URL for the PR.

    Returns:
        Dict mapping thread IDs to their full thread response, or None
        if the API call fails.
    """
    try:
        response = requests_module.get(threads_url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        threads = data.get("value", [])
        return {t["id"]: t for t in threads if "id" in t}
    except Exception:
        return None
