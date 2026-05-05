"""Spec parser for E.2 — FR extraction with priority and user-story mapping.

Extracts FR identifiers from spec.md along with their associated user-story
priority (P1/P2/P3) and builds user-story-to-FR mappings.
"""

from __future__ import annotations

import re

from .models import FRInfo

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

_FR_RE = re.compile(r"\bFR-\d+\b", re.IGNORECASE)
_US_HEADING_RE = re.compile(
    r"^#{2,4}\s+User\s+Story\s+(\d+)",
    re.IGNORECASE | re.MULTILINE,
)
_PRIORITY_RE = re.compile(r"\bP([123])\b", re.IGNORECASE)
_PRIORITY_HEADING_RE = re.compile(r"Priority:\s*P([123])", re.IGNORECASE)
_ACCEPTANCE_SCENARIOS_RE = re.compile(
    r"\*\*Acceptance\s+Scenarios?\*\*\s*:?",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_frs_with_priority(spec_content: str) -> list[FRInfo]:
    """Extract FR identifiers with associated user-story priority.

    Priority determination:
    - If an FR appears within a user story section that has an explicit
      priority (P1/P2/P3), the FR inherits that priority.
    - If the priority cannot be determined, defaults to non-P1 (priority=2)
      and sets ``priority_ambiguous=True`` per FR-001.

    Returns a deduplicated list in document order.
    """
    us_sections = parse_user_story_sections(spec_content)

    # Build FR -> (priority, user_story_number, ambiguous, scenarios) lookup
    fr_to_info: dict[str, tuple[int, int | None, bool, list[str]]] = {}
    for us_idx, section in enumerate(us_sections, start=1):
        us_num = section.get("us_number", us_idx)
        priority = section.get("priority")
        frs_in_section = section.get("frs", [])
        scenarios = section.get("acceptance_scenarios", [])
        for fr_id in frs_in_section:
            key = fr_id.upper()
            if key not in fr_to_info:
                if priority is not None:
                    fr_to_info[key] = (priority, us_num, False, scenarios)
                else:
                    fr_to_info[key] = (2, us_num, True, scenarios)

    # Also find FRs in the requirements section that may not appear in US sections
    all_frs = _extract_unique_frs(spec_content)
    results: list[FRInfo] = []
    seen: set[str] = set()

    for fr_id in all_frs:
        key = fr_id.upper()
        if key in seen:  # pragma: no cover
            continue  # pragma: no cover
        seen.add(key)

        if key in fr_to_info:
            priority, user_story_num, ambiguous, scenarios = fr_to_info[key]
            results.append(
                FRInfo(
                    fr_id=fr_id,
                    priority=priority,
                    user_story=user_story_num,
                    priority_ambiguous=ambiguous,
                    acceptance_scenarios=scenarios,
                )
            )
        else:
            # FR not in any user story section — ambiguous priority
            results.append(
                FRInfo(
                    fr_id=fr_id,
                    priority=2,
                    user_story=None,
                    priority_ambiguous=True,
                    acceptance_scenarios=[],
                )
            )

    return results


def parse_user_story_sections(spec_content: str) -> list[dict]:
    """Parse user story sections from spec content.

    Returns a list of dicts, each with:
    - "title": The user story heading text
    - "us_number": int, the actual story number from the heading
    - "priority": int (1, 2, or 3) or None if undetermined
    - "text": The full section text
    - "frs": list of FR identifiers found in the section
    """
    lines = spec_content.split("\n")
    sections: list[dict] = []

    # Find user story headings by pattern
    us_starts: list[tuple[int, int, str]] = []
    for i, line in enumerate(lines):
        match = _US_HEADING_RE.match(line)
        if match:
            us_starts.append((i, int(match.group(1)), line.strip()))
            continue
        # Also match "### User Story N —" pattern with various separators
        alt_match = re.match(
            r"^#{2,4}\s+User\s+Story\s+(\d+)\s*[—–\-:]",
            line,
            re.IGNORECASE,
        )
        if alt_match and not match:  # pragma: no cover
            us_starts.append((i, int(alt_match.group(1)), line.strip()))  # pragma: no cover

    if not us_starts:
        return []

    # Determine section boundaries
    for idx, (start_line, us_num, title) in enumerate(us_starts):
        if idx + 1 < len(us_starts):
            end_line = us_starts[idx + 1][0]
        else:
            # For the last user story, end at the next heading of the same
            # or higher level rather than running to EOF.  This prevents
            # content from subsequent sections (e.g. "## Requirements")
            # being incorrectly associated with the last user story.
            us_level = len(title) - len(title.lstrip("#"))
            end_line = len(lines)
            for i in range(start_line + 1, len(lines)):
                line = lines[i]
                if not line.startswith("#"):
                    continue
                heading_level = len(line) - len(line.lstrip("#"))
                if heading_level > 0 and heading_level <= us_level:
                    end_line = i
                    break

        section_text = "\n".join(lines[start_line:end_line])

        # Extract priority from section text
        priority = _extract_priority_from_section(section_text)

        # Extract FR references within the section
        frs = _extract_unique_frs(section_text)

        # Extract acceptance scenarios from the section
        scenarios = _extract_acceptance_scenarios(section_text, us_num)

        sections.append(
            {
                "title": title,
                "us_number": us_num,
                "priority": priority,
                "text": section_text,
                "frs": frs,
                "acceptance_scenarios": scenarios,
            }
        )

    return sections


def build_us_to_fr_mapping(
    us_sections: list[dict],
) -> dict[int, list[str]]:
    """Build a mapping from user story number to FR identifiers.

    Uses the actual story number from the heading (``us_number`` key) when
    available, falling back to the 1-based section index for backward
    compatibility with older section dicts that lack ``us_number``.

    Args:
        us_sections: Output from ``parse_user_story_sections()``.

    Returns:
        Dict like ``{1: ["FR-001", "FR-003"], 2: ["FR-002"]}``.
    """
    mapping: dict[int, list[str]] = {}
    for idx, section in enumerate(us_sections, start=1):
        key = section.get("us_number", idx)
        mapping[key] = section.get("frs", [])
    return mapping


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_unique_frs(text: str) -> list[str]:
    """Extract unique FR identifiers from text in document order."""
    seen: set[str] = set()
    result: list[str] = []
    for match in _FR_RE.finditer(text):
        fr_id = match.group(0)
        key = fr_id.upper()
        if key not in seen:
            seen.add(key)
            result.append(fr_id)
    return result


def _extract_priority_from_section(section_text: str) -> int | None:
    """Extract priority (P1/P2/P3) from a user story section.

    Checks for explicit "Priority: Pn" pattern first, then parenthetical
    "Priority: Pn" context, then falls back to any P1/P2/P3 word-boundary
    mention in the section.
    """
    # Look for explicit priority annotation
    heading_match = _PRIORITY_HEADING_RE.search(section_text)
    if heading_match:
        return int(heading_match.group(1))

    # Fallback: look for P1/P2/P3 in parenthetical context
    paren_match = re.search(r"\(.*?Priority:\s*P([123]).*?\)", section_text, re.IGNORECASE)
    if paren_match:  # pragma: no cover
        return int(paren_match.group(1))  # pragma: no cover

    # Last resort: any word-boundary P1/P2/P3 mention in the section
    priority_match = _PRIORITY_RE.search(section_text)
    if priority_match:
        return int(priority_match.group(1))

    return None


def _extract_acceptance_scenarios(section_text: str, us_number: int) -> list[str]:
    """Extract acceptance scenario identifiers from a user story section.

    Looks for an "**Acceptance Scenarios**:" heading followed by numbered items.
    Returns identifiers in the format "US{n}/AS{m}" (e.g., "US1/AS1", "US1/AS2").
    Returns an empty list if no acceptance scenarios are found.
    """
    lines = section_text.split("\n")
    scenarios: list[str] = []
    in_scenarios = False

    for line in lines:
        # Detect start of acceptance scenarios block
        if _ACCEPTANCE_SCENARIOS_RE.search(line):
            in_scenarios = True
            continue

        if in_scenarios:
            # Numbered list item (e.g., "1. **Given** ...")
            numbered_match = re.match(r"^\s*(\d+)\.\s+", line)
            if numbered_match:
                scenario_num = int(numbered_match.group(1))
                scenarios.append(f"US{us_number}/AS{scenario_num}")
            elif line.strip() == "" or line.startswith("#"):
                # Blank line or new heading — end of scenarios block
                if scenarios:
                    break
            # Non-numbered continuation lines are part of previous scenario

    return scenarios
