"""
Jira description and label formatting utilities.
"""

import os
from typing import List, Optional


def format_bullet_list(items: Optional[List[str]], placeholder: Optional[str] = None) -> str:
    """
    Format items as a Jira bullet list.

    Preserves existing bullets, headings, and numbered items.

    Args:
        items: List of items to format
        placeholder: Text to show if items is empty

    Returns:
        Formatted bullet list string
    """
    if not items:
        if placeholder:
            return f"* {placeholder}"
        return ""

    lines = []
    for item in items:
        if not item or not item.strip():
            continue
        line = item.strip()
        # Check if already has bullet, heading, or numbered list prefix
        if (
            line.startswith("*")
            or line.startswith("#")
            or line[0].isdigit()
            and ". " in line[:5]
            or line.startswith("h")
            and line[1:3].replace(".", "").isdigit()
        ):
            lines.append(line)
        else:
            lines.append(f"* {line}")

    return "\n".join(lines) if lines else (f"* {placeholder}" if placeholder else "")


def build_user_story_description(
    role: str,
    desired_outcome: str,
    benefit: str,
    acceptance_criteria: Optional[List[str]] = None,
    additional_information: Optional[List[str]] = None,
) -> str:
    """
    Build a Jira description in user story format.

    Args:
        role: Who the user is
        desired_outcome: What they want
        benefit: Why they want it
        acceptance_criteria: List of acceptance criteria
        additional_information: Additional context

    Returns:
        Formatted Jira description
    """
    lines = [
        f"*As a* {role.strip()},",
        f"*I would like* {desired_outcome.strip()},",
        f"*so that* {benefit.strip()}.",
        "",
        "h3. +Acceptance Criteria+",
        format_bullet_list(acceptance_criteria, "Document acceptance criteria here."),
    ]

    additional = format_bullet_list(additional_information)
    if additional:
        lines.extend(["", "h3. +Additional Information+", additional])

    # Add reviewer if available
    reviewer = os.environ.get("JIRA_EMAIL") or os.environ.get("JIRA_USERNAME")
    if reviewer:
        lines.extend(["", "h3. +Reviewer+", reviewer])

    return "\n".join(lines)


def merge_labels(
    custom_labels: Optional[List[str]] = None,
    include_zu_priorisieren: bool = True,
    include_created_by_ai: bool = True,
    include_ready_for_ai: bool = True,
) -> List[str]:
    """
    Merge custom labels with default labels, removing duplicates.

    Args:
        custom_labels: User-provided labels
        include_zu_priorisieren: Include zuPriorisieren label
        include_created_by_ai: Include createdByAiAgent label
        include_ready_for_ai: Include readyForAiAgent label

    Returns:
        Merged, deduplicated list of labels
    """
    result = ["createdWithDflyAiHelpers"]
    seen = {"createdwithdflyaihelpers"}  # lowercase for case-insensitive deduplication

    if custom_labels:
        for label in custom_labels:
            if label and label.lower() not in seen:
                result.append(label)
                seen.add(label.lower())

    optional_labels = []
    if include_zu_priorisieren:
        optional_labels.append("zuPriorisieren")
    if include_created_by_ai:
        optional_labels.append("createdByAiAgent")
    if include_ready_for_ai:
        optional_labels.append("readyForAiAgent")

    for label in optional_labels:
        if label.lower() not in seen:
            result.append(label)
            seen.add(label.lower())

    return result
