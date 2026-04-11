"""Plan-phase context budget management.

Enforces a character budget on content passed to the planning workflow step.
All reduction techniques are deterministic — no LLM summarization.
"""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass

DEFAULT_CONTEXT_BUDGET: int = 32_000

_TRUNCATION_MARKER: str = "\n[…truncated]"


class ContextBudgetError(Exception):
    """Raised when content cannot be reduced to fit the budget."""


class ReductionStage(enum.Enum):
    """Stage reached during context budget enforcement."""

    PASSTHROUGH = "passthrough"
    REDUCED = "reduced"
    TRUNCATED = "truncated"
    SUMMARY_ONLY = "summary_only"


@dataclass(frozen=True)
class BudgetResult:
    """Outcome of a context budget enforcement call."""

    description: str
    comments: str
    stage: ReductionStage
    original_chars: int
    final_chars: int
    budget: int


# ---------------------------------------------------------------------------
# Reduction helpers — pure, deterministic, no I/O
# ---------------------------------------------------------------------------

# Pre-compiled patterns for performance
# CommonMark allows up to 3 leading spaces before a fenced code block.
# The closing fence must use the same indentation and fence character.
# NOTE: CommonMark allows the closing fence to be *longer* than the opening
# fence, but this regex requires an exact-length match via backreference.
# In practice, virtually all Markdown uses matching-length fences (e.g.
# ``` ... ```), so this covers real-world usage without the complexity
# of a variable-length closing fence pattern.
_FENCED_CODE_BLOCK_RE = re.compile(
    r"^(?P<indent>[ ]{0,3})(?P<fence>`{3,}|~{3,})[^\n]*\n"
    r"(.*?)\n"
    r"(?P=indent)(?P=fence)[ \t]*$",
    re.MULTILINE | re.DOTALL,
)
_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_IMAGE_MD_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_IMAGE_HTML_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
# Jira image syntax requires a file-extension dot to avoid false positives
# on non-image text like !important! or !warning!.
_IMAGE_JIRA_RE = re.compile(r"![\w/-]*\.[\w./-]+!")
_BASE64_DATA_URI_RE = re.compile(r"data:image/[^;]+;base64,[A-Za-z0-9+/=]+")
_HEADING_RE = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
# Underscore-based bold/italic is intentionally NOT stripped because the
# patterns collide with snake_case identifiers (foo_bar) and dunder names
# (__init__, __main__) that commonly appear in technical specifications.
# Asterisk-based emphasis (**bold**, *italic*) handles the vast majority of
# real-world Markdown emphasis; leaving underscore emphasis intact is the
# safest choice for this reduction pipeline.
_ITALIC_RE = re.compile(r"\*(.+?)\*")
_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_HR_RE = re.compile(r"^---+\s*$", re.MULTILINE)
_MULTI_BLANK_RE = re.compile(r"\n{3,}")
_TRAILING_SPACE_RE = re.compile(r"[ \t]+$", re.MULTILINE)
_MULTI_SPACE_RE = re.compile(r"[ \t]{2,}")


def strip_markdown_formatting(text: str) -> str:
    """Remove markdown formatting while preserving plain text and code content.

    Strips headings markers, bold, italic, link syntax, and horizontal rules.
    Preserves the content of fenced code blocks, indented code blocks, and
    inline code spans.
    """
    if not text:
        return text

    # Protect code blocks: extract them, replace with placeholders, strip
    # formatting from the rest, then restore code blocks.
    placeholders: list[str] = []

    def _protect_fenced(match: re.Match[str]) -> str:
        idx = len(placeholders)
        placeholders.append(match.group(0))
        return f"\x00CODEBLOCK{idx}\x00"

    result = _FENCED_CODE_BLOCK_RE.sub(_protect_fenced, text)

    # Protect indented code blocks (4-space or 1-tab indent)
    indented_lines: list[str] = []
    output_lines: list[str] = []
    in_indented_block = False

    for line in result.split("\n"):
        is_indented = line.startswith("    ") or line.startswith("\t")
        is_blank = not line.strip()

        if is_indented and not in_indented_block:
            in_indented_block = True
            indented_lines = [line]
        elif in_indented_block and (is_indented or is_blank):
            indented_lines.append(line)
        elif in_indented_block:
            # End of indented block — protect it
            block_text = "\n".join(indented_lines)
            idx = len(placeholders)
            placeholders.append(block_text)
            output_lines.append(f"\x00CODEBLOCK{idx}\x00")
            in_indented_block = False
            indented_lines = []
            output_lines.append(line)
        else:
            output_lines.append(line)

    if in_indented_block:
        block_text = "\n".join(indented_lines)
        idx = len(placeholders)
        placeholders.append(block_text)
        output_lines.append(f"\x00CODEBLOCK{idx}\x00")

    result = "\n".join(output_lines)

    # Protect inline code spans
    def _protect_inline(match: re.Match[str]) -> str:
        idx = len(placeholders)
        placeholders.append(match.group(0))
        return f"\x00CODEBLOCK{idx}\x00"

    result = _INLINE_CODE_RE.sub(_protect_inline, result)

    # Now strip markdown formatting from the non-code parts
    result = _HEADING_RE.sub("", result)
    result = _BOLD_RE.sub(r"\1", result)
    result = _ITALIC_RE.sub(r"\1", result)
    result = _LINK_RE.sub(r"\1", result)
    result = _HR_RE.sub("", result)

    # Restore protected blocks
    for idx, block in enumerate(placeholders):
        result = result.replace(f"\x00CODEBLOCK{idx}\x00", block)

    return result


def remove_image_references(text: str) -> str:
    """Remove image references from text.

    Handles markdown images ``![alt](url)``, HTML ``<img>`` tags,
    Jira ``!image!`` syntax, and base64 data URIs.
    """
    if not text:
        return text

    result = _IMAGE_MD_RE.sub("", text)
    result = _IMAGE_HTML_RE.sub("", result)
    result = _BASE64_DATA_URI_RE.sub("", result)
    result = _IMAGE_JIRA_RE.sub("", result)
    return result


def collapse_whitespace(text: str) -> str:
    """Collapse excessive whitespace while preserving structure.

    - Multiple blank lines → single blank line
    - Trailing spaces on lines → removed
    - Multiple spaces within a line → single space (preserving leading indent)
    """
    if not text:
        return text

    # Remove trailing spaces from each line
    result = _TRAILING_SPACE_RE.sub("", text)

    # Collapse multiple blank lines to a single blank line
    result = _MULTI_BLANK_RE.sub("\n\n", result)

    # Collapse multiple inline spaces (but preserve leading indent)
    lines = result.split("\n")
    collapsed: list[str] = []
    for line in lines:
        if not line:
            collapsed.append(line)
            continue
        # Find leading whitespace
        stripped = line.lstrip()
        leading = line[: len(line) - len(stripped)]
        # Collapse spaces in the non-leading portion
        body = _MULTI_SPACE_RE.sub(" ", stripped)
        collapsed.append(leading + body)

    return "\n".join(collapsed)


def hard_truncate(text: str, limit: int) -> str:
    """Truncate *text* to at most *limit* characters at a word boundary.

    Appends the truncation marker (``\\n[…truncated]``) when truncation
    occurs.  The marker includes a leading newline so it always starts on
    its own line in the output.
    """
    if not text or len(text) <= limit:
        return text

    marker = _TRUNCATION_MARKER
    if limit <= len(marker):
        return marker[:limit]

    available = limit - len(marker)
    # Find the last word boundary (space or newline) within the available space
    truncated = text[:available]
    last_space = max(truncated.rfind(" "), truncated.rfind("\n"))
    if last_space > 0:
        truncated = truncated[:last_space]

    return truncated + marker


def validate_content_shape(text: str) -> bool:
    """Check whether *text* contains substantive content.

    Returns ``True`` when the trimmed text contains at least 3 alphanumeric
    characters.  Empty, whitespace-only, or punctuation-only strings return
    ``False``.
    """
    if not text or not text.strip():
        return False
    alphanumeric = re.findall(r"[A-Za-z0-9]", text.strip())
    return len(alphanumeric) >= 3


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def enforce_context_budget(
    description: str,
    comments: str,
    budget: int = DEFAULT_CONTEXT_BUDGET,
) -> BudgetResult:
    """Enforce a character budget on plan-phase content.

    Applies a deterministic fallback chain:

    1. **Passthrough** — if combined length ≤ budget, return as-is.
    2. **Reduced** — strip markdown formatting, images, and whitespace.
    3. **Truncated** — hard-truncate the combined content.
    4. **Summary-only** — drop comments, truncate description only.

    Raises :class:`ContextBudgetError` if budget ≤ 0 or no stage can produce
    valid, in-budget content.
    """
    if budget <= 0:
        raise ContextBudgetError(
            f"Budget must be a positive integer (got {budget}). "
            "Cannot produce any content with a zero or negative budget."
        )

    # Account for the separator newline the CLI inserts between description
    # and comments when both are non-empty.  This keeps ``final_chars``
    # accurate relative to what actually appears on stdout.
    separator = 1 if description and comments else 0
    original_chars = len(description) + len(comments) + separator

    # --- Stage 1: Passthrough ---
    if original_chars <= budget:
        return BudgetResult(
            description=description,
            comments=comments,
            stage=ReductionStage.PASSTHROUGH,
            original_chars=original_chars,
            final_chars=original_chars,
            budget=budget,
        )

    # --- Stage 2: Reduced ---
    reduced_desc = collapse_whitespace(remove_image_references(strip_markdown_formatting(description))).strip()
    reduced_comments = collapse_whitespace(remove_image_references(strip_markdown_formatting(comments))).strip()
    reduced_separator = 1 if reduced_desc and reduced_comments else 0
    reduced_chars = len(reduced_desc) + len(reduced_comments) + reduced_separator

    # Validate that reduction didn't strip content down to nothing meaningful
    # (e.g. input that was only image references or markup). If invalid, fall
    # through to truncation/summary stages which apply their own validation.
    reduced_combined = reduced_desc + reduced_comments
    if reduced_chars <= budget and validate_content_shape(reduced_combined):
        return BudgetResult(
            description=reduced_desc,
            comments=reduced_comments,
            stage=ReductionStage.REDUCED,
            original_chars=original_chars,
            final_chars=reduced_chars,
            budget=budget,
        )

    # --- Stage 3: Truncated ---
    # Truncate the combined reduced description/comments content and return it
    # in `description`, clearing `comments` because the truncated payload is not
    # split back into separate fields at this stage.
    combined = (
        reduced_desc + "\n" + reduced_comments
        if reduced_desc and reduced_comments
        else reduced_desc + reduced_comments
    )
    truncated = hard_truncate(combined, budget)
    truncated_chars = len(truncated)

    if truncated_chars <= budget and validate_content_shape(truncated):
        return BudgetResult(
            description=truncated,
            comments="",
            stage=ReductionStage.TRUNCATED,
            original_chars=original_chars,
            final_chars=truncated_chars,
            budget=budget,
        )

    # --- Stage 4: Summary-only ---
    # Drop comments entirely, truncate description
    summary_desc = hard_truncate(reduced_desc, budget)
    summary_chars = len(summary_desc)

    if summary_chars <= budget and validate_content_shape(summary_desc):
        return BudgetResult(
            description=summary_desc,
            comments="",
            stage=ReductionStage.SUMMARY_ONLY,
            original_chars=original_chars,
            final_chars=summary_chars,
            budget=budget,
        )

    # --- Stage 5: Permanent failure ---
    raise ContextBudgetError(
        f"Cannot reduce content to fit budget of {budget} characters. "
        f"Original size: {original_chars}, after reduction: {reduced_chars}. "
        "All fallback stages exhausted (passthrough, reduced, truncated, summary-only). "
        "Consider reducing the source issue content manually or increasing AGDT_PLAN_CONTEXT_BUDGET."
    )
