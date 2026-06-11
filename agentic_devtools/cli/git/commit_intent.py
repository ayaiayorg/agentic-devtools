"""
Commit intent resolution for split create/amend title parameters.

This module determines whether a commit operation should create a new commit
or overwrite (amend) an existing one based on CLI flags and state keys.
"""

import re
import sys
from dataclasses import dataclass
from typing import Literal

# Matches a conventional-commit title line, e.g. "feat(#42): description",
# "feat([#42](https://github.com/org/repo/issues/42)): title", or
# "fix!: something". The scope is matched with `.*?` (lazy) rather than
# `[^)]*` to accommodate GitHub Markdown link scopes that contain nested
# parens. Require the commit type to be followed by a valid Conventional
# Commits delimiter (`(`, `!`, or `:`) so prose such as "feature: ..." is not
# misidentified as a stale title stanza.
_CONVENTIONAL_COMMIT_TITLE_RE = re.compile(
    r"^(?:feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(?:\((?:.*?)\)!?:|!?:) .+"
)


@dataclass
class CommitIntent:
    """Resolved commit intent with mode, title, body, and full message.

    Attributes:
        mode: One of "create", "overwrite", or "legacy".
        title: The commit title (None for legacy mode).
        body: The resolved body (for create mode; None for overwrite/legacy).
        full_message: The fully assembled commit message.
    """

    mode: Literal["create", "overwrite", "legacy"]
    title: str | None
    body: str | None
    full_message: str


def _remove_leading_title_stanza(body: str, create_title: str) -> str:
    """Drop a duplicated leading title stanza while preserving body whitespace."""
    body_lines = body.split("\n")
    first_line = body_lines[0].strip() if body_lines else ""
    has_blank_separator = len(body_lines) >= 2 and body_lines[1].strip() == ""

    if first_line and _CONVENTIONAL_COMMIT_TITLE_RE.match(first_line):
        if has_blank_separator:
            body = "\n".join(body_lines[2:])
        else:
            body = "\n".join(body_lines[1:])
    elif body_lines and first_line == create_title.strip():
        start_index = 2 if has_blank_separator else 1
        body = "\n".join(body_lines[start_index:])
    if body.endswith("\n"):
        body = body[:-1]

    return body


def resolve_commit_intent(
    *,
    cli_commit_message_title: str | None,
    cli_overwrite_commit_message_title: str | None,
    cli_commit_message: str | None,
    state_commit_message_title: str | None,
    state_overwrite_commit_message_title: str | None,
    state_commit_message: str | None,
) -> CommitIntent:
    """Resolve the commit intent from explicit CLI flags and state-key inputs.

    Resolution logic:

    1. CLI flags take precedence over state keys.
    2. If both create-intent and overwrite-intent signals are present → exit 1.
    3. Create-path: title + body from ``commit_message`` source.
    4. Overwrite-path: title only (body is preserved from existing commit).
    5. Legacy-path: full ``commit_message`` used as-is.

    Args:
        cli_commit_message_title: ``--commit-message-title`` CLI flag value.
        cli_overwrite_commit_message_title: ``--overwrite-commit-message-title`` CLI flag value.
        cli_commit_message: ``--commit-message`` CLI flag value.
        state_commit_message_title: ``commit_message_title`` state key value.
        state_overwrite_commit_message_title: ``overwrite_commit_message_title`` state key value.
        state_commit_message: ``commit_message`` state key value.

    Returns:
        A :class:`CommitIntent` describing the resolved mode and message.

    Raises:
        SystemExit: On conflict (both create and overwrite signals present)
            or when required inputs are missing.
    """
    # Resolve effective values (CLI takes precedence over state)
    create_title = cli_commit_message_title if cli_commit_message_title is not None else state_commit_message_title
    overwrite_title = (
        cli_overwrite_commit_message_title
        if cli_overwrite_commit_message_title is not None
        else state_overwrite_commit_message_title
    )
    commit_message = cli_commit_message if cli_commit_message is not None else state_commit_message

    # Track the human-readable source of each title for accurate error messages.
    create_title_source = (
        "--commit-message-title" if cli_commit_message_title is not None else "commit_message_title state key"
    )
    overwrite_title_source = (
        "--overwrite-commit-message-title"
        if cli_overwrite_commit_message_title is not None
        else "overwrite_commit_message_title state key"
    )

    if create_title is not None and create_title.strip() == "":
        print(f"Error: {create_title_source} cannot be empty or whitespace.", file=sys.stderr)
        sys.exit(1)

    if overwrite_title is not None and overwrite_title.strip() == "":
        print(f"Error: {overwrite_title_source} cannot be empty or whitespace.", file=sys.stderr)
        sys.exit(1)

    if overwrite_title and cli_commit_message is not None:
        print(
            "Error: Cannot combine --overwrite-commit-message-title with --commit-message. "
            "Overwrite mode preserves the existing commit body.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Conflict detection: both create-intent and overwrite-intent present
    if create_title and overwrite_title:
        print(
            f"Error: Cannot use both {create_title_source} and {overwrite_title_source} simultaneously.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Create path
    if create_title:
        # Body comes from commit_message source
        body = _remove_leading_title_stanza(commit_message or "", create_title)

        if body:
            full_message = f"{create_title}\n\n{body}"
        else:
            full_message = create_title

        return CommitIntent(
            mode="create",
            title=create_title,
            body=body if body else None,
            full_message=full_message,
        )

    # Overwrite path
    if overwrite_title:
        # Body will be resolved at call site (from existing commit)
        # For now, full_message is just the title; the caller will
        # compose the final message with the preserved body.
        return CommitIntent(
            mode="overwrite",
            title=overwrite_title,
            body=None,
            full_message=overwrite_title,
        )

    # Legacy path
    if commit_message:
        return CommitIntent(
            mode="legacy",
            title=None,
            body=None,
            full_message=commit_message,
        )

    # No message source available
    print(
        "Error: No commit message source available. Use --commit-message-title, "
        "--overwrite-commit-message-title, --commit-message, or set commit_message in state.",
        file=sys.stderr,
    )
    sys.exit(1)
