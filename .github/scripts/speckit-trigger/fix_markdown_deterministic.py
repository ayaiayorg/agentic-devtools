#!/usr/bin/env python3
"""Deterministic fixers for common markdownlint violations.

Applies reliable, fast fixes for rules that the LLM remediation loop
frequently fails to resolve:

  * MD040 (fenced-code-language): Adds ``text`` language identifier to bare
    fenced code blocks that have no language specifier.
  * MD056 (table-column-count): Normalizes table data rows to match the
    column count of the header row (pads short rows, truncates excess cells).

Usage:
    python fix_markdown_deterministic.py FILE [FILE ...]

Files are edited in place.  Non-existent files are skipped with a warning.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Regex matching a bare fence opener with NO language identifier.
# Captures: (leading whitespace 0-3 spaces)(fence marker: 3+ backticks or 3+ tildes)
# CommonMark spec: opening code fences may be indented 0-3 spaces only.
_BARE_FENCE_RE = re.compile(r"^( {0,3})(`{3,}|~{3,})\s*$")

# Regex matching a fence opener WITH a language identifier (used to detect
# when we're entering a code block that already has a language).
# CommonMark spec: opening code fences may be indented 0-3 spaces only.
_FENCE_OPEN_RE = re.compile(r"^( {0,3})(`{3,}|~{3,})")


def fix_md040(lines: list[str]) -> list[str]:
    """Add ``text`` language identifier to bare fenced code blocks (MD040).

    Processes lines in order, tracking whether we are inside a fenced code
    block to avoid modifying content lines that happen to look like fences.
    """
    result: list[str] = []
    in_fence = False
    fence_marker = ""

    for line in lines:
        stripped = line.rstrip("\n")

        if not in_fence:
            m = _BARE_FENCE_RE.match(stripped)
            if m:
                # Bare fence opener — add 'text' language
                indent, marker = m.group(1), m.group(2)
                result.append(f"{indent}{marker}text\n")
                in_fence = True
                fence_marker = marker
                continue

            # Check if this is a fence opener with a language (enter block)
            m2 = _FENCE_OPEN_RE.match(stripped)
            if m2:
                indent, marker = m2.group(1), m2.group(2)
                after_marker = stripped[len(indent) + len(marker):]
                # Only enter fence if there's content after the marker
                # (language identifier) or if it's a closing fence for a
                # never-opened block (shouldn't happen in valid markdown)
                if after_marker.strip():
                    in_fence = True
                    fence_marker = marker
            result.append(line)
        else:
            # Inside a fence — check for closing fence.
            # Per CommonMark spec, a closing fence can have 0-3 spaces of
            # indentation regardless of the opener's indent, and must use the
            # same fence character with at least as many markers.
            close_re = re.compile(
                r"^ {0,3}" + re.escape(fence_marker[0]) + r"{" + str(len(fence_marker)) + r",}\s*$"
            )
            if close_re.match(stripped):
                in_fence = False
                fence_marker = ""
            result.append(line)

    return result


def _has_code_block_indent(line: str) -> bool:
    """Return True if line has >= 4 columns of leading indentation (CommonMark).

    Tabs advance to the next tab stop (multiple of 4).  This catches mixed
    prefixes like `` \t`` that the simple 4-space / leading-tab checks miss.
    """
    col = 0
    for ch in line:
        if ch == " ":
            col += 1
        elif ch == "\t":
            col = (col // 4 + 1) * 4
        else:
            break
        if col >= 4:
            return True
    return False


def _is_table_line(line: str) -> bool:
    """Return True if the line looks like a markdown table row."""
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|")


def _is_separator_row(line: str) -> bool:
    """Return True if the line is a table separator (e.g., |---|---|)."""
    stripped = line.strip()
    if not (stripped.startswith("|") and stripped.endswith("|")):
        return False
    # Remove outer pipes and check cells contain only dashes, colons, spaces
    inner = stripped[1:-1]
    cells = inner.split("|")
    return all(re.match(r"^[\s:-]*-[\s:-]*$", c) for c in cells)


def _split_table_cells(line: str) -> list[str]:
    """Split a table row into cells, respecting escaped pipes."""
    stripped = line.strip()
    # Remove outer pipes
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    # Split on unescaped pipes (not preceded by backslash)
    cells = re.split(r"(?<!\\)\|", stripped)
    return cells


def _count_columns(line: str) -> int:
    """Count the number of columns in a table row."""
    return len(_split_table_cells(line))


def _normalize_row(line: str, expected_cols: int) -> str:
    """Pad or truncate a table row to match expected column count."""
    cells = _split_table_cells(line)
    current_cols = len(cells)

    if current_cols == expected_cols:
        return line  # No change needed

    if current_cols < expected_cols:
        # Pad with empty cells
        cells.extend([" "] * (expected_cols - current_cols))
    else:
        # Truncate excess cells
        cells = cells[:expected_cols]

    # Preserve original leading whitespace (e.g., tables indented under list items)
    leading = line[: len(line) - len(line.lstrip(" "))]
    return leading + "| " + " | ".join(c.strip() or " " for c in cells) + " |\n"


def _normalize_separator_row(line: str, expected_cols: int) -> str:
    """Pad or truncate a table separator row to match expected column count.

    Unlike _normalize_row, this preserves separator-cell formatting (dashes,
    colons for alignment) rather than treating cells as data content.
    """
    cells = _split_table_cells(line)
    current_cols = len(cells)

    if current_cols == expected_cols:
        return line  # No change needed

    if current_cols < expected_cols:
        # Pad with separator cells (---)
        cells.extend([" --- "] * (expected_cols - current_cols))
    else:
        # Truncate excess cells
        cells = cells[:expected_cols]

    # Rebuild with proper separator formatting
    formatted = []
    for c in cells:
        stripped = c.strip()
        if not stripped or not re.match(r"^[:\s-]*-[:\s-]*$", stripped):
            # Not a valid separator cell — use default
            stripped = "---"
        formatted.append(f" {stripped} ")
    # Preserve original leading whitespace (e.g., tables indented under list items)
    leading = line[: len(line) - len(line.lstrip(" "))]
    return leading + "|" + "|".join(formatted) + "|\n"


def fix_md056(lines: list[str]) -> list[str]:
    """Normalize table column counts to match header row (MD056).

    Identifies table blocks (consecutive lines starting and ending with |),
    determines expected column count from the header row, and normalizes
    all data rows to match.
    """
    result: list[str] = []
    i = 0
    in_fence = False
    fence_marker = ""

    while i < len(lines):
        line = lines[i]
        stripped = line.rstrip("\n")

        # Track fenced code blocks to avoid modifying tables inside them
        if not in_fence:
            m = _FENCE_OPEN_RE.match(stripped)
            if m:
                marker = m.group(2)
                # Opening fence (bare or with language) — enter block
                in_fence = True
                fence_marker = marker
                result.append(line)
                i += 1
                continue
        else:
            # Closing fence: same char, at least same count, 0-3 spaces indent
            if re.match(
                r"^ {0,3}" + re.escape(fence_marker[0]) + r"{" + str(len(fence_marker)) + r",}\s*$",
                stripped,
            ):
                in_fence = False
                fence_marker = ""
            result.append(line)
            i += 1
            continue

        # Not in a fence — check for table blocks
        # Skip indented code blocks per CommonMark (tab, 4+ spaces, or mixed)
        if _has_code_block_indent(line):
            result.append(line)
            i += 1
            continue

        if _is_table_line(stripped):
            # Collect the entire table block
            table_lines: list[str] = []
            while i < len(lines) and _is_table_line(lines[i].rstrip("\n")):
                # Stop collecting if line is an indented code block
                if _has_code_block_indent(lines[i]):
                    break
                table_lines.append(lines[i])
                i += 1

            # Need at least header + separator (2 rows) and second row
            # must be a valid separator to confirm this is a real table
            if len(table_lines) >= 2 and _is_separator_row(table_lines[1].rstrip("\n")):
                # Header is the first row
                expected_cols = _count_columns(table_lines[0].rstrip("\n"))

                for j, tline in enumerate(table_lines):
                    if j == 0:
                        # Keep header as-is (it defines the expected count)
                        result.append(tline)
                    elif j == 1:
                        # Only the second row is the table separator
                        result.append(_normalize_separator_row(tline, expected_cols))
                    else:
                        # Data row — normalize to expected column count
                        result.append(_normalize_row(tline, expected_cols))
            else:
                # Not a real table, just pass through
                result.extend(table_lines)
        else:
            result.append(line)
            i += 1

    return result


def fix_file(path: Path) -> bool:
    """Apply all deterministic fixes to a single file. Returns True if modified."""
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        print(f"Warning: Could not read {path}: {e}", file=sys.stderr)
        return False

    lines = content.splitlines(keepends=True)
    # Ensure last line has a newline for consistent processing
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"

    # Apply fixers in sequence
    fixed_lines = fix_md040(lines)
    fixed_lines = fix_md056(fixed_lines)

    new_content = "".join(fixed_lines)

    if new_content != content:
        path.write_text(new_content, encoding="utf-8")
        return True
    return False


def main() -> None:
    """CLI entry point: accept file paths as arguments, fix in place."""
    if len(sys.argv) < 2:
        print("Usage: fix_markdown_deterministic.py FILE [FILE ...]", file=sys.stderr)
        sys.exit(1)

    files = [Path(arg) for arg in sys.argv[1:]]
    modified_count = 0

    for fpath in files:
        if not fpath.exists():
            print(f"Warning: File not found, skipping: {fpath}", file=sys.stderr)
            continue
        if not fpath.suffix == ".md":
            continue

        if fix_file(fpath):
            modified_count += 1
            print(f"  [Deterministic Fix] Modified: {fpath.name}", file=sys.stderr)

    if modified_count > 0:
        print(
            f"  [Deterministic Fix] {modified_count} file(s) modified.",
            file=sys.stderr,
        )
    else:
        print("  [Deterministic Fix] No changes needed.", file=sys.stderr)


if __name__ == "__main__":
    main()
