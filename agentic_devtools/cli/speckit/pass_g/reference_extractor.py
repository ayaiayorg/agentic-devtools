"""Extract code references from plan Markdown text (FR-001, FR-004)."""

from __future__ import annotations

import re

from .models import Reference, ReferenceKind

# Patterns for extracting references from plan text
_BACKTICK_RE = re.compile(r"`([^`\n]+)`")
_CODE_FENCE_RE = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)
_FILE_EXT_RE = re.compile(
    r"\.(py|toml|yml|yaml|json|md|txt|cfg|ini|sh|ts|js|rs|go)$"
)


def extract_references(plan_text: str) -> list[Reference]:
    """Extract code references from *plan_text* (FR-001, FR-004, FR-015).

    Extracts backtick-quoted identifiers and code fence contents.
    Deduplicates by reference text, preserving first occurrence line number.
    """
    if not plan_text.strip():
        return []

    references: list[Reference] = []
    seen: set[str] = set()

    lines = plan_text.splitlines()

    # Extract backtick-quoted identifiers
    for line_num, line in enumerate(lines, start=1):
        for match in _BACKTICK_RE.finditer(line):
            text = match.group(1).strip()
            if text and text not in seen:
                seen.add(text)
                kind = classify_reference_kind(text)
                references.append(
                    Reference(
                        text=text,
                        kind=kind,
                        plan_location=f"L{line_num}",
                        context_sentence=line.strip(),
                    )
                )

    # Extract identifiers from code fences
    for match in _CODE_FENCE_RE.finditer(plan_text):
        fence_content = match.group(1)
        # Find line number of the fence start
        fence_start = plan_text[: match.start()].count("\n") + 1
        for rel_line, fence_line in enumerate(fence_content.splitlines()):
            for ident_match in _BACKTICK_RE.finditer(fence_line):
                text = ident_match.group(1).strip()
                if text and text not in seen:  # pragma: no cover – inline pass catches these first
                    seen.add(text)
                    kind = classify_reference_kind(text)
                    references.append(
                        Reference(
                            text=text,
                            kind=kind,
                            plan_location=f"L{fence_start + rel_line + 1}",
                            context_sentence=fence_line.strip(),
                        )
                    )
            # Also extract bare identifiers that look like file paths
            for bare_match in re.finditer(
                r"(?<!\w)([a-zA-Z_][\w/.-]*(?:\.py|\.toml|\.yml|\.yaml|\.json|\.md))\b",
                fence_line,
            ):
                text = bare_match.group(1).strip()
                if text and text not in seen:
                    seen.add(text)
                    kind = classify_reference_kind(text)
                    references.append(
                        Reference(
                            text=text,
                            kind=kind,
                            plan_location=f"L{fence_start + rel_line + 1}",
                            context_sentence=fence_line.strip(),
                        )
                    )

    return references


def classify_reference_kind(text: str) -> ReferenceKind:
    """Classify a reference text into a ReferenceKind (FR-001, FR-007)."""
    # File path: contains / or ends with known extension
    if "/" in text or _FILE_EXT_RE.search(text):
        return ReferenceKind.FILE_PATH

    # CLI command: starts with agdt- or contains dashes typical of CLI
    if text.startswith("agdt-") or text.startswith("agdt_"):
        return ReferenceKind.CLI_COMMAND

    # Module path: dotted notation without uppercase start
    if "." in text and not text[0].isupper():
        return ReferenceKind.MODULE_PATH

    # Class name: starts with uppercase, CamelCase
    if text[0].isupper() and re.match(r"^[A-Z][a-zA-Z0-9]*$", text):
        return ReferenceKind.CLASS_NAME

    # Method name: contains a dot with lowercase after
    if "." in text and text.split(".")[-1][0:1].islower():
        return ReferenceKind.METHOD_NAME

    # Function name: snake_case starting lowercase
    if re.match(r"^[a-z_][a-z0-9_]*$", text) and len(text) > 2:
        return ReferenceKind.FUNCTION_NAME

    return ReferenceKind.UNCLASSIFIED
