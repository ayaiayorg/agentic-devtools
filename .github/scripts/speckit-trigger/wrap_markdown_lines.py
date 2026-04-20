#!/usr/bin/env python3
"""Wrap long lines in markdown files to satisfy MD013 (line-length).

Used as a best-effort post-processing step after SpecKit pipeline phases
generate spec.md / plan.md / tasks.md / checklists/*.md / analysis-report.md.
LLM output frequently produces single-line paragraphs and list items that
exceed the 200-character MD013 limit; wrapping them at word boundaries
here reduces the load on the downstream markdownlint remediation loop.

The following block types are preserved verbatim (never wrapped):

  * Fenced code blocks (``` or ~~~)
  * Table rows that clearly look like Markdown tables (for example, rows
    with leading/trailing pipes, multiple column separators, or the
    separator row)
  * Indented code blocks (4-space or tab-indented lines)
  * YAML front matter at start of file (--- ... ---)
  * Heading lines (# ... — rare for these to be overlong; wrapping would
    create multiple headings)
  * Lines containing a markdownlint inline disable comment

Raw HTML blocks are not specially tracked; lines that are not otherwise
recognized as preserved block types may still be wrapped.

Wrapped block types:

  * Regular paragraph text
  * List items (preserves list marker + continuation indent so markdown
    treats the continuation as part of the same item)
  * Blockquotes (preserves the '> ' prefix on continuation lines)

Usage:
    python wrap_markdown_lines.py FILE [FILE ...]
    python wrap_markdown_lines.py --max-line-length 200 FILE [FILE ...]

Files are edited in place. Files not modified are untouched (no change to
mtime). Non-existent files are skipped with a warning; this is by design so
that callers can glob across optional artifacts without guarding each path.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Default to the MD013 line_length configured in .markdownlint-cli2.jsonc.
# Keep these two values in sync.
DEFAULT_MAX_LINE_LENGTH = 200

# List item marker: leading whitespace + bullet/ordered marker + space.
# Captures:
#   1: leading whitespace (indent)
#   2: marker (-, *, +, or "N.")
_LIST_MARKER_RE = re.compile(r"^(\s*)([-*+]|\d+\.)(\s+)")

# Blockquote prefix: one or more '>' each optionally followed by a space.
_BLOCKQUOTE_RE = re.compile(r"^((?:>\s?)+)")

# Heading: ATX style (# through ######) followed by space.
_HEADING_RE = re.compile(r"^#{1,6}\s")

# Also matches fences nested inside blockquotes (for example: '> ```'),
# while keeping the actual fence marker in capture group 2 so existing
# open/close tracking can ignore the blockquote prefix.
_FENCE_RE = re.compile(r"^(\s*)(?:(?:>\s?)+\s*)?(```+|~~~+)")

# Link reference definition: [label]: url "title"
_LINK_REF_RE = re.compile(r"^\s{0,3}\[[^\]]+\]:\s")

# markdownlint inline comment (<!-- markdownlint-disable ... -->) — never wrap,
# otherwise we break the directive.
_MARKDOWNLINT_COMMENT_RE = re.compile(r"<!--\s*markdownlint-")


def _is_table_row(line: str) -> bool:
    """Return True if the line looks like a Markdown table row.

    A table row typically starts or ends with a '|', or contains multiple
    '|' characters separating columns, or is a separator row.
    This stricter heuristic prevents wrapping from being skipped for prose
    (e.g. list items) that simply happen to contain a single pipe.
    """
    stripped = line.strip()
    if not stripped:
        return False

    # Escaped pipe at start -> treat as prose.
    if stripped.startswith("\\|"):
        return False

    # Remove escaped pipes so they don't count towards the heuristic
    unescaped = stripped.replace(r"\|", "")

    if "|" not in unescaped:
        return False

    if unescaped.startswith("|") or unescaped.endswith("|"):
        return True

    if unescaped.count("|") >= 2:
        return True

    # Check for separator row (only hyphens, colons, spaces, and the pipe itself)
    if re.match(r"^[\s\|\-:]+$", unescaped):
        return True

    return False


def _is_indented_code(line: str) -> bool:
    """Return True if the line begins with 4+ spaces or a tab (indented code)."""
    if line.startswith("\t"):
        return True
    return line.startswith("    ")


def _wrap_prose(
    text: str,
    subsequent_indent: str,
    width: int,
    initial_indent_width: int = 0,
) -> list[str]:
    """Word-wrap *text* to *width*, prefixing continuation lines with *subsequent_indent*.

    The first returned line has no extra indent (the caller prepends any
    list marker / blockquote prefix); its visible width is assumed to already
    include *initial_indent_width* characters consumed by that marker.
    Subsequent lines are prefixed with *subsequent_indent*.  Returns at least
    one line; returns the original text as a single-element list if no
    wrapping is possible (for example, a single long word).

    Unlike ``str.split()``, this preserves existing whitespace runs and any
    trailing spaces already present in *text* so wrapping only introduces
    line breaks rather than changing Markdown content.
    """
    segments = re.findall(r"\S+|\s+", text)
    if not segments or all(segment.isspace() for segment in segments):
        return [text]

    lines: list[str] = []
    current = ""
    current_prefix = ""  # empty on first line, *subsequent_indent* on later lines
    current_extra_width = initial_indent_width  # marker on first line

    for segment in segments:
        if not current:
            # First segment on this line — always take it, even if oversize.
            current = segment
            continue

        if segment.isspace():
            # Preserve original whitespace exactly, including repeated spaces
            # and trailing double-space hard breaks in Markdown.
            # However, check if appending would exceed the width budget;
            # if so, wrap before the whitespace so emitted lines still obey
            # the width limit.
            candidate = current + segment
            visible_width = len(current_prefix) + current_extra_width + len(candidate)
            if visible_width <= width:
                current = candidate
                continue

            lines.append(current_prefix + current)
            current_prefix = subsequent_indent
            current_extra_width = 0
            current = ""
            continue

        candidate = current + segment
        visible_width = len(current_prefix) + current_extra_width + len(candidate)
        if visible_width <= width:
            current = candidate
            continue

        lines.append(current_prefix + current)
        current_prefix = subsequent_indent
        current_extra_width = 0
        current = segment

    if current:
        lines.append(current_prefix + current)
    return lines


def _wrap_list_item(line: str, width: int) -> list[str]:
    """Wrap a list item, preserving its marker and continuation indent."""
    m = _LIST_MARKER_RE.match(line)
    if not m:
        return [line]
    leading, marker, sep = m.group(1), m.group(2), m.group(3)
    rest = line[m.end() :]
    if not rest.strip():
        return [line]
    # Continuation indent must align past the marker so CommonMark treats
    # the continuation as part of the same list item.
    indent = leading + " " * (len(marker) + len(sep))
    first_line_consumed = len(leading) + len(marker) + len(sep)
    wrapped = _wrap_prose(rest, indent, width, initial_indent_width=first_line_consumed)
    if not wrapped:
        return [line]
    wrapped[0] = leading + marker + sep + wrapped[0]
    return wrapped


def _wrap_blockquote(line: str, width: int) -> list[str]:
    """Wrap a blockquote line, preserving the '> ' prefix on each line."""
    m = _BLOCKQUOTE_RE.match(line)
    if not m:
        return [line]
    prefix = m.group(1)
    rest = line[m.end() :]
    if not rest.strip():
        return [line]
    wrapped = _wrap_prose(rest, prefix, width, initial_indent_width=len(prefix))
    if not wrapped:
        return [line]
    wrapped[0] = prefix + wrapped[0]
    return wrapped


def _wrap_paragraph(line: str, width: int) -> list[str]:
    """Wrap a regular paragraph line, preserving any leading whitespace."""
    leading = line[: len(line) - len(line.lstrip(" "))]
    rest = line[len(leading) :]
    if not rest.strip():
        return [line]
    wrapped = _wrap_prose(rest, leading, width, initial_indent_width=len(leading))
    if not wrapped:
        return [line]
    wrapped[0] = leading + wrapped[0]
    return wrapped


def wrap_markdown_text(text: str, width: int = DEFAULT_MAX_LINE_LENGTH) -> str:
    """Return *text* with prose lines longer than *width* wrapped.

    See the module docstring for the list of preserved / wrapped block types.
    """
    if width <= 0:
        raise ValueError(f"width must be positive (got {width})")

    # Detect trailing newline so we can restore it; splitlines() drops it.
    had_trailing_newline = text.endswith("\n")
    lines = text.splitlines()
    out: list[str] = []

    in_fence = False
    fence_marker: str | None = None  # either "```" or "~~~"
    in_front_matter = False
    # YAML front matter only counts if the very first line is exactly "---".
    if lines and lines[0].strip() == "---":
        in_front_matter = True

    for idx, line in enumerate(lines):
        # --- Front matter handling --------------------------------------
        if in_front_matter:
            out.append(line)
            if idx > 0 and line.strip() == "---":
                in_front_matter = False
            continue

        # --- Fenced code block handling ---------------------------------
        fence_match = _FENCE_RE.match(line)
        if in_fence:
            out.append(line)
            if fence_match and fence_marker is not None:
                # To close a fence, the marker must be the same character,
                # have length >= the opening marker, and be indented 3 or fewer spaces.
                close_char = fence_match.group(2)[0]
                close_len = len(fence_match.group(2))
                open_char = fence_marker[0]
                open_len = len(fence_marker)
                indent_len = len(fence_match.group(1))
                remainder = line[fence_match.end() :]

                if (
                    close_char == open_char
                    and close_len >= open_len
                    and indent_len <= 3
                    and not remainder.strip()
                ):
                    in_fence = False
                    fence_marker = None
            continue
        if fence_match and len(fence_match.group(1)) <= 3:
            in_fence = True
            fence_marker = fence_match.group(2)
            out.append(line)
            continue

        # --- Preserved line types ---------------------------------------
        if len(line) <= width:
            out.append(line)
            continue
        if _is_table_row(line):
            out.append(line)
            continue
        if _is_indented_code(line):
            out.append(line)
            continue
        if _HEADING_RE.match(line):
            out.append(line)
            continue
        if _LINK_REF_RE.match(line):
            out.append(line)
            continue
        if _MARKDOWNLINT_COMMENT_RE.search(line):
            out.append(line)
            continue

        # --- Wrapping ---------------------------------------------------
        blockquote_match = _BLOCKQUOTE_RE.match(line)
        if blockquote_match:
            prefix = blockquote_match.group(1)
            rest = line[blockquote_match.end() :]
            if _LIST_MARKER_RE.match(rest):
                # It's a list item inside a blockquote: wrap the rest and prepend the prefix.
                # The effective width is reduced by the length of the prefix.
                # Clamp the derived width so nested blockquote prefixes combined
                # with a small user-supplied width cannot pass zero/negative values
                # into _wrap_list_item.
                adjusted_width = max(1, width - len(prefix))
                wrapped_rest = _wrap_list_item(rest, adjusted_width)
                out.extend([prefix + w for w in wrapped_rest])
            else:
                out.extend(_wrap_blockquote(line, width))
        elif _LIST_MARKER_RE.match(line):
            out.extend(_wrap_list_item(line, width))
        else:
            out.extend(_wrap_paragraph(line, width))

    result = "\n".join(out)
    if had_trailing_newline:
        result += "\n"
    return result


def wrap_file(path: Path, width: int = DEFAULT_MAX_LINE_LENGTH) -> bool:
    """Wrap long lines in *path* in place. Return True if the file changed."""
    original = path.read_text(encoding="utf-8")
    wrapped = wrap_markdown_text(original, width=width)
    if wrapped == original:
        return False
    path.write_text(wrapped, encoding="utf-8")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--max-line-length",
        type=int,
        default=DEFAULT_MAX_LINE_LENGTH,
        help=f"Maximum line length (default: {DEFAULT_MAX_LINE_LENGTH}).",
    )
    parser.add_argument(
        "files",
        nargs="+",
        help="Markdown files to wrap in place.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-file progress output on stderr.",
    )
    args = parser.parse_args(argv)

    if args.max_line_length <= 0:
        print(
            f"Error: --max-line-length must be positive (got {args.max_line_length})",
            file=sys.stderr,
        )
        return 2

    changed = 0
    for raw_path in args.files:
        path = Path(raw_path)
        if not path.exists():
            if not args.quiet:
                print(f"[wrap_markdown_lines] Skipping (not found): {raw_path}", file=sys.stderr)
            continue
        try:
            if wrap_file(path, width=args.max_line_length):
                changed += 1
                if not args.quiet:
                    print(f"[wrap_markdown_lines] Wrapped: {raw_path}", file=sys.stderr)
        except OSError as exc:
            print(f"[wrap_markdown_lines] Error wrapping {raw_path}: {exc}", file=sys.stderr)
            return 1

    if not args.quiet:
        print(
            f"[wrap_markdown_lines] {changed} of {len(args.files)} files modified",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
